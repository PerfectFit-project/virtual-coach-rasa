import logging
from celery import Celery
from datetime import date, datetime, timedelta
from state_machine.state_machine_utils import (compute_previous_day,
                                               create_new_date, get_dialog_completion_state,
                                               get_execution_week, get_intervention_component,
                                               get_activity_completion_state,
                                               get_all_scheduled_occurrence,
                                               get_last_component_state,
                                               get_next_planned_date, get_next_scheduled_occurrence,
                                               get_hrs_last_branch,
                                               get_preferred_date_time,
                                               get_quit_date, get_pa_group, get_start_date,
                                               is_new_week, plan_and_store, plan_every_day_range,
                                               reschedule_dialog,
                                               retrieve_tracking_day,
                                               run_uncompleted_dialog, run_option_menu,
                                               save_fsm_state_in_db,
                                               schedule_next_execution, store_completed_dialog,
                                               store_scheduled_dialog, update_execution_week,
                                               update_fsm_dialog_running_status,
                                               dialogs_to_be_completed, get_component_id,
                                               reschedule_weekly_reflection,
                                               plan_new_date_notifications)
from state_machine.const import (ACTIVITY_C2_9_DAY_TRIGGER, FUTURE_SELF_INTRO, GOAL_SETTING,
                                 TRACKING_DURATION, TIMEZONE, PREPARATION_GA, PAUSE_AND_TRIGGER,
                                 MAX_PREPARATION_DURATION, HIGH_PA_GROUP,
                                 EXECUTION_DURATION_WEEKS, TIME_DELTA_PA_NOTIFICATION, REDIS_URL,
                                 RESCHEDULE_DIALOG, TRIGGER_INTENT)
from state_machine.state import State
from virtual_coach_db.helper.definitions import (Components, ComponentsTriggers,
                                                 Notifications, NotificationsTriggers)

celery = Celery(broker=REDIS_URL)


class OnboardingState(State):

    def __init__(self, user_id: int):
        super().__init__(user_id, celery)
        self.state = State.ONBOARDING
        self.user_id = user_id
        self.new_state = None

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=1)

        if dialog == Components.PREPARATION_INTRODUCTION:
            logging.info('Prep completed, starting profile creation')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.PROFILE_CREATION,
                           phase_id=1)

        elif dialog == Components.PROFILE_CREATION:
            logging.info('Profile creation completed, starting med talk')

            dialog_id = get_intervention_component(
                Components.MEDICATION_TALK).intervention_component_id

            trigger_time = datetime.now() + timedelta(seconds=30)
            # store record in db
            store_scheduled_dialog(user_id=self.user_id,
                                   dialog_id=dialog_id,
                                   phase_id=1,
                                   planned_date=trigger_time,
                                   last_time=trigger_time)

            # pause the conversation and then trigger the dialog
            celery.send_task(PAUSE_AND_TRIGGER,
                             (self.user_id,
                              ComponentsTriggers.MEDICATION_TALK,
                              datetime.now() + timedelta(seconds=30),
                              True))

        elif dialog == Components.MEDICATION_TALK:
            # check if the track behavior dialog has to be started (i.e. the coach triggered

            # the currently completed medication talk) or not.
            if self.is_track_behaviour_next():
                logging.info('Med talk completed, starting track behavior')
                plan_and_store(user_id=self.user_id,
                               dialog=Components.TRACK_BEHAVIOR,
                               phase_id=1)
                # notifications for tracking have to be activated
                self.schedule_tracking_notifications()

        elif dialog == Components.TRACK_BEHAVIOR:
            logging.info('Tack behavior completed, starting future self')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.FUTURE_SELF_LONG,
                           phase_id=1)

        elif dialog == Components.FUTURE_SELF_LONG:
            self.schedule_next_dialogs()
            # upon the completion of the future self dialog,
            # the new state can be triggered
            self.set_new_state(TrackingState(self.user_id))

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_user_trigger(self, dialog):
        if dialog in (Components.FIRST_AID_KIT,
                      Components.FIRST_AID_KIT_VIDEO,
                      Components.RELAPSE_DIALOG):
            # dialog not available in this phase
            run_option_menu(user_id=self.user_id)
        elif dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=1)

    def run(self):
        logging.info('Onboarding State running')
        save_fsm_state_in_db(self.user_id, self.state)
        # the first dialog is the introduction video
        plan_and_store(user_id=self.user_id,
                       dialog=Components.PREPARATION_INTRODUCTION,
                       phase_id=1)

    def is_track_behaviour_next(self) -> bool:
        """
        Determines if the track behavior dialog has to be run after the completion of the
        medication talk dialog or not.

        Returns: True if the track behavior dialog has to run, False otherwise

        """
        # if the profile creation hasn't been completed, don't run the track behavior
        intro = get_intervention_component(Components.PROFILE_CREATION)
        intro_state = get_last_component_state(self.user_id, intro.intervention_component_id)

        if not intro_state.completed:
            return False

        # if a tack behavior has been already planned by the VC,
        # this is not the case where we need to run it again.
        track_state = get_intervention_component(Components.TRACK_BEHAVIOR)
        component_state = get_last_component_state(self.user_id,
                                                   track_state.intervention_component_id)

        # if the component is already in the DB,
        if component_state is not None:
            return False

        return True

    def schedule_next_dialogs(self):
        # get the data on which the user has started the intervention
        # (day 1 of preparation phase)
        start_date = get_start_date(self.user_id)

        # on day 9 at 10 a.m. send future self
        fs_time = create_new_date(start_date=start_date,
                                  time_delta=FUTURE_SELF_INTRO)

        # if the expected scheduling time is already passed,
        # don't show the short version of the future self dialog

        # (the long version has just been shown)
        if fs_time.date() <= date.today():
            return

        plan_and_store(user_id=self.user_id,
                       dialog=Components.FUTURE_SELF_SHORT,
                       planned_date=fs_time,
                       phase_id=1)

    def schedule_tracking_notifications(self):
        """
        Schedule the notifications from the day after the tracking dialog completions
        to day 9 of the preparation phase
        """
        first_date = date.today() + timedelta(days=1)
        last_date = get_start_date(self.user_id) + timedelta(days=TRACKING_DURATION-1)

        plan_every_day_range(user_id=self.user_id,
                             dialog=Notifications.TRACK_NOTIFICATION,
                             phase_id=1,
                             first_date=first_date,
                             last_date=last_date)


class TrackingState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.TRACKING

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=1)

        if dialog == Components.FUTURE_SELF_SHORT:
            logging.info('Future self completed')
            self.set_new_state(GoalsSettingState(self.user_id))

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_user_trigger(self, dialog):
        if (dialog in (Components.FIRST_AID_KIT, Components.FIRST_AID_KIT_VIDEO)) \
                and not get_dialog_completion_state(self.user_id, Components.FIRST_AID_KIT_VIDEO):
            # if the introductory video of the first aid kit has not been executed,
            # the first aid kit cannot be executed
            run_option_menu(self.user_id)
        elif dialog == Components.RELAPSE_DIALOG:
            # the relapse dialog is not available in this phase
            run_option_menu(self.user_id)
        elif dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=1)

    def run(self):
        logging.info('Starting Tracking state')
        save_fsm_state_in_db(self.user_id, self.state)

        current_date = date.today()
        self.check_if_end_date(current_date)

    def on_new_day(self, current_date: date):
        logging.info('current date: %s', current_date)

        # at day 7 activity C2.9 has to be proposed
        start_date = get_start_date(self.user_id)
        choose_sport_completed = get_activity_completion_state(self.user_id, 29)
        if ((current_date - start_date).days >= ACTIVITY_C2_9_DAY_TRIGGER
                and not choose_sport_completed):
            if self.check_if_general_activity_dialog_exists():
                run_uncompleted_dialog(self.user_id, dialog_preference=Components.GENERAL_ACTIVITY)
            else:
                plan_and_store(user_id=self.user_id,
                               dialog=Components.GENERAL_ACTIVITY,
                               phase_id=1)

        self.check_if_end_date(current_date)

    def check_if_end_date(self, date_to_check: date) -> bool:
        tracking_day = retrieve_tracking_day(self.user_id, date_to_check)
        # the Goal Setting state starts on day 10 of the intervention

        if tracking_day is None:
            logging.warning(f'Tracking day is not found for user {self.user_id}')
        elif tracking_day >= TRACKING_DURATION:
            self.set_new_state(GoalsSettingState(self.user_id))
            return True

        return False

    def check_if_general_activity_dialog_exists(self):
        """
        Check if there is an uncompleted general activity dialog in the database for the given user.
        """
        general_activity_id = get_component_id(Components.GENERAL_ACTIVITY)
        uncompleted_dialogs = dialogs_to_be_completed(self.user_id)
        dialog_ids = list(map(lambda dialog: dialog.intervention_component_id, uncompleted_dialogs))

        return general_activity_id in dialog_ids


class GoalsSettingState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.GOALS_SETTING

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=1)

        if dialog == Components.GOAL_SETTING:
            logging.info('Goal setting completed, starting first aid kit')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.FIRST_AID_KIT_VIDEO,
                           planned_date=datetime.now() + timedelta(minutes=1),
                           phase_id=1)
            # after the completion of the goal setting dialog, the execution
            # phase can be planned
            self.plan_buffer_phase_dialogs()
            self.plan_execution_start_dialog()
            self.schedule_pa_notifications()

        elif dialog == Components.FIRST_AID_KIT_VIDEO:
            logging.info('First aid kit completed, starting buffering state')
            self.set_new_state(BufferState(self.user_id))

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_new_day(self, current_date: date):
        self.check_if_end_date(current_date)

    def on_user_trigger(self, dialog):
        # the relapse dialog is not available in this phase
        if dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        # in this phase a dialog can be continued
        elif dialog == Components.RELAPSE_DIALOG:
            run_option_menu(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=1)

    def plan_buffer_phase_dialogs(self):
        quit_date = get_quit_date(self.user_id)
        start_date = get_start_date(self.user_id)

        if (quit_date - start_date).days >= PREPARATION_GA:
            planned_date = create_new_date(start_date=start_date, time_delta=PREPARATION_GA)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           planned_date=planned_date,
                           phase_id=1)

        if (delta := (quit_date - start_date).days) >= MAX_PREPARATION_DURATION:
            planned_date = create_new_date(start_date=start_date,
                                           time_delta=delta)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           planned_date=planned_date,
                           phase_id=1)

    def plan_execution_start_dialog(self):
        # this is the intro video to be sent the first time
        # the execution starts (not after lapse/relapse)
        quit_date = get_quit_date(self.user_id)
        planned_date = create_new_date(start_date=quit_date, minute=5)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.EXECUTION_INTRODUCTION,
                       planned_date=planned_date,
                       phase_id=1)

    def schedule_pa_notifications(self):
        # the notifications are delivered according to the group of the user. Group 1 gets
        # a notification with the steps goal every day. Group 2 gets a notification with steps
        # and intensity goal twice a week, 1 and 4 days after the GA dialog.
        # The group is determined during the GA dialog.

        pa_group = get_pa_group(self.user_id)

        first_date = date.today() + timedelta(days=1)
        # until the execution starts
        last_date = get_quit_date(self.user_id)

        if pa_group == HIGH_PA_GROUP:
            # every 3 days
            for day in range((last_date - first_date).days)[0::3]:
                planned_date = create_new_date(start_date=first_date,
                                               time_delta=day)

                plan_and_store(user_id=self.user_id,
                               dialog=Notifications.PA_INTENSITY_MINUTES_NOTIFICATION,
                               planned_date=planned_date,
                               phase_id=2)
        # every day (default group 1)
        else:
            plan_every_day_range(user_id=self.user_id,
                                 dialog=Notifications.PA_STEP_GOAL_NOTIFICATION,
                                 phase_id=2,
                                 first_date=first_date,
                                 last_date=last_date)

    def run(self):
        save_fsm_state_in_db(self.user_id, self.state)

        start_date = get_start_date(self.user_id)

        # if the starting of this phase is after the expected one
        # launch immediately the goal setting
        if date.today() >= start_date + timedelta(days=GOAL_SETTING):
            gs_time = None

        else:
            # plan the Goals setting dialog for tomorrow
            gs_time = create_new_date(start_date=date.today(),
                                      time_delta=1)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.GOAL_SETTING,
                       planned_date=gs_time,
                       phase_id=1)

    def check_if_end_date(self, current_date: date):
        quit_date = get_quit_date(self.user_id)

        if quit_date is None:
            logging.warning(f'Quit date is not found for user {self.user_id}')
        elif current_date >= quit_date:
            logging.info('Goals setting state ended, starting execution state')

            # on the quit date, notify the user that today is the quit date
            if current_date == quit_date:
                celery.send_task(TRIGGER_INTENT,
                                 (self.user_id, NotificationsTriggers.QUIT_DATE_NOTIFICATION))

            self.set_new_state(ExecutionRunState(self.user_id))


class BufferState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.BUFFER

    def run(self):
        logging.info('Buffer State running')
        save_fsm_state_in_db(self.user_id, self.state)
        # if the user sets the quit date to the day after the goal
        # setting dialog, the buffer phase can also be immediately over
        self.check_if_end_date(date.today())

    def on_new_day(self, current_date: date):
        self.check_if_end_date(current_date)

    def on_user_trigger(self, dialog: str):
        if dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        # the relapse dialog is not available in this phase
        elif dialog == Components.RELAPSE_DIALOG:
            run_option_menu(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=1)

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=2)

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def check_if_end_date(self, current_date: date):
        quit_date = get_quit_date(self.user_id)

        if quit_date is None:
            logging.warning(f'Quit date is not found for user {self.user_id}')
        elif current_date >= quit_date:
            logging.info('Buffer state ended, starting execution state')

            # on the quit date, notify the user that today is the quit date
            if current_date == quit_date:
                celery.send_task(TRIGGER_INTENT,
                                 (self.user_id, NotificationsTriggers.QUIT_DATE_NOTIFICATION))

            self.set_new_state(ExecutionRunState(self.user_id))


class ExecutionRunState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.EXECUTION_RUN

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=2)

        if dialog == Components.EXECUTION_INTRODUCTION:
            logging.info(f'Execution intro completed for user {self.user_id}')

        elif dialog == Components.GENERAL_ACTIVITY:
            # check if the weekly reflection has be triggered
            if self.is_weekly_reflection_next():
                # pause the conversation for 1 minute, while the latest messages
                # of the general activity are sent, and then trigger the weekly reflection

                trigger_time = datetime.now() + timedelta(minutes=1)

                dialog_id = get_intervention_component(
                    Components.WEEKLY_REFLECTION).intervention_component_id

                # store record in db
                store_scheduled_dialog(user_id=self.user_id,
                                       dialog_id=dialog_id,
                                       phase_id=2,
                                       planned_date=trigger_time,
                                       last_time=trigger_time)

                # pause the conversation and then trigger the dialog
                celery.send_task(PAUSE_AND_TRIGGER,
                                 (self.user_id,
                                  ComponentsTriggers.WEEKLY_REFLECTION,
                                  datetime.now() + timedelta(minutes=1),
                                  True))

        elif dialog == Components.WEEKLY_REFLECTION:
            logging.info('Weekly reflection completed')

            quit_date = get_quit_date(self.user_id)
            current_date = date.today()

            # if the quit date is in the future, it has been reset
            # during the weekly reflection dialog
            if quit_date > current_date:
                # if a new quit date has been set, the weekly reflection might be rescheduled,
                # a notification on the day before and on the new date are planned.
                # Then we go back to the buffer state
                reschedule_weekly_reflection(self.user_id, quit_date)
                plan_new_date_notifications(self.user_id, quit_date)
                self.set_new_state(BufferState(self.user_id))
                store_completed_dialog(user_id=self.user_id,
                                       dialog=Components.RELAPSE_DIALOG,
                                       phase_id=3)
                return

            week = get_execution_week(user_id=self.user_id)

            # on the first week, the execution of the general activity dialog 
            # has to be planned for week 2
            if week == 1:

                schedule_next_execution(user_id=self.user_id,
                                        dialog=Components.GENERAL_ACTIVITY,
                                        current_date=datetime.now(),
                                        phase_id=2)

                # after the weekly reflection is completed, the notifications
                # for the next week are planned
                self.schedule_pa_notifications()

            # if in week 3 or 8 of the execution, run future self after
            # completing the weekly reflection
            elif week in [3, 8]:
                logging.info('Starting future self')

                # pause the conversation for 1 minute, while the latest messages
                # of the weekly reflection are sent, and then trigger the future self video

                trigger_time = datetime.now() + timedelta(minutes=1)

                dialog_id = get_intervention_component(
                    Components.FUTURE_SELF_SHORT).intervention_component_id

                # store record in db
                store_scheduled_dialog(user_id=self.user_id,
                                       dialog_id=dialog_id,
                                       phase_id=2,
                                       planned_date=trigger_time,
                                       last_time=trigger_time)

                # pause the conversation and then trigger the dialog
                celery.send_task(PAUSE_AND_TRIGGER,
                                 (self.user_id,
                                  ComponentsTriggers.FUTURE_SELF_SHORT,
                                  datetime.now() + timedelta(minutes=1),
                                  True))

                # plan the execution for the next week
                schedule_next_execution(user_id=self.user_id,
                                        dialog=Components.WEEKLY_REFLECTION,
                                        current_date=datetime.now(),
                                        phase_id=2)

                # after the weekly reflection is completed, the notifications
                # for the next week are planned
                self.schedule_pa_notifications()

            # if in week 12, the execution is finished. Start the closing state
            elif week >= EXECUTION_DURATION_WEEKS:
                self.set_new_state(ClosingState(self.user_id))

            # in the other weeks, plan the next execution of the weekly reflection
            else:
                schedule_next_execution(user_id=self.user_id,
                                        dialog=Components.WEEKLY_REFLECTION,
                                        current_date=datetime.now(),
                                        phase_id=2)

                # after the weekly reflection is completed, the notifications
                # for the next week are planned
                self.schedule_pa_notifications()

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=2)

    def on_user_trigger(self, dialog: str):
        # in this phase a dialog can be continued
        if dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=2)

        if dialog in [Components.RELAPSE_DIALOG, Components.RELAPSE_DIALOG_SYSTEM]:
            self.set_new_state(RelapseState(self.user_id))

    def on_new_day(self, current_date: date):

        quit_date = get_quit_date(self.user_id)

        # in case the current day of the week is the same as the one set in the
        # quit_date (and is not the same date), a new week started.
        # Thus, the execution week must be updated
        if is_new_week(current_date, quit_date):
            # get the current week number
            week_number = get_execution_week(self.user_id)

            # increase the week number by one
            # we don't compute directly the number of weeks, because in case of relapse, the
            # number of weeks doesn't increase
            update_execution_week(self.user_id, week_number + 1)

        # if the preferred day is passed, and the weekly reflection has not been
        # completed nor planned, send it now.

        # get the date of the previous preferred day
        last_preferred_day = compute_previous_day(self.user_id, current_date)
        quit_date = get_quit_date(self.user_id)

        # make sure that today is not the preferred day, and that the previous
        # preferred day was in the running phase (i.e., after the quit date )
        if last_preferred_day != current_date and last_preferred_day > quit_date:
            component = get_intervention_component(Components.WEEKLY_REFLECTION)

            # convert to datetime
            pref_timedate = datetime.combine(last_preferred_day, datetime.min.time())

            # get the general activity dialog that have been scheduled after the
            # last preferred date
            next_scheduled = get_next_scheduled_occurrence(self.user_id,
                                                           component.intervention_component_id,
                                                           pref_timedate)
            # if none have been scheduled, trigger one
            if not next_scheduled:
                plan_and_store(user_id=self.user_id,
                               dialog=Components.WEEKLY_REFLECTION,
                               phase_id=2)

    def run(self):
        logging.info("Running state %s", self.state)
        save_fsm_state_in_db(self.user_id, self.state)

        # if the execution week is not 0, it means that we are returning to
        # this state after a relapse, and the week should not be reset.
        # also, the planning of the general activity has to be done only on the first time the
        # execution state is reached
        if get_execution_week(self.user_id) == 0:
            update_execution_week(self.user_id, 1)

            # plan the execution for the next week.

            schedule_next_execution(user_id=self.user_id,
                                    dialog=Components.GENERAL_ACTIVITY,
                                    current_date=datetime.now(),
                                    phase_id=2)

            self.schedule_pa_notifications()

    def schedule_pa_notifications(self):
        # the notifications are delivered according to the group of the user. Group 1 gets
        # a notification with the steps goal every day. Group 2 gets a notification with steps
        # and intensity goal twice a week, 1 and 4 days after the GA dialog.
        # The group is determined during the GA dialog.

        pa_group = get_pa_group(self.user_id)

        if pa_group == HIGH_PA_GROUP:

            planned_date_1 = create_new_date(start_date=date.today(),
                                             time_delta=1)

            plan_and_store(user_id=self.user_id,
                           dialog=Notifications.PA_INTENSITY_MINUTES_NOTIFICATION,
                           planned_date=planned_date_1,
                           phase_id=2)

            planned_date_4 = create_new_date(start_date=date.today(),
                                             time_delta=TIME_DELTA_PA_NOTIFICATION)

            plan_and_store(user_id=self.user_id,
                           dialog=Notifications.PA_INTENSITY_MINUTES_NOTIFICATION,
                           planned_date=planned_date_4,
                           phase_id=2)

        else:

            first_date = date.today() + timedelta(days=1)
            # until the next GA dialog
            last_date = get_next_planned_date(self.user_id, datetime.now())

            plan_every_day_range(user_id=self.user_id,
                                 dialog=Notifications.PA_STEP_GOAL_NOTIFICATION,
                                 phase_id=2,
                                 first_date=first_date,
                                 last_date=last_date.date())

    def is_weekly_reflection_next(self) -> bool:
        """
        Determines if the weekly reflection dialog has to be run after the completion of the
        general activity dialog or not.

        Returns: True if the weekly reflection has to run, False otherwise

        """
        #  just in the first 2 weeks the weekly reflection follows the GA
        week = get_execution_week(user_id=self.user_id)
        if week > 2:
            return False

        # if the execution introduction hasn't been completed, don't run the weekly reflection
        intro = get_intervention_component(Components.EXECUTION_INTRODUCTION)
        intro_state = get_last_component_state(self.user_id, intro.intervention_component_id)

        if not intro_state.completed:
            return False

        # if a GA is still planned by the VC for a future date, and it has not been completed
        # this is not the case where we need to run the weekly reflection
        ga_component = get_intervention_component(Components.GENERAL_ACTIVITY)
        next_planned = get_all_scheduled_occurrence(self.user_id,
                                                    ga_component.intervention_component_id,
                                                    datetime.now(tz=TIMEZONE))

        for occurrence in next_planned:
            # if last_time is None, the component was not triggered by the user
            if not occurrence.completed and occurrence.last_time is None:
                return False

        return True


class RelapseState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.RELAPSE

    def run(self):
        logging.info("Running state %s", self.state)
        save_fsm_state_in_db(self.user_id, self.state)

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=3)

        if dialog in [Components.RELAPSE_DIALOG,
                      Components.RELAPSE_DIALOG_HRS,
                      Components.RELAPSE_DIALOG_LAPSE,
                      Components.RELAPSE_DIALOG_RELAPSE,
                      Components.RELAPSE_DIALOG_PA,
                      Components.RELAPSE_DIALOG_SYSTEM]:

            # When a specific branch of the relapse dialog has been completed,
            # we need to mark the general relapse dialog as completed
            if dialog != Components.RELAPSE_DIALOG:
                store_completed_dialog(user_id=self.user_id,
                                       dialog=Components.RELAPSE_DIALOG,
                                       phase_id=3)

            quit_date = get_quit_date(self.user_id)
            current_date = date.today()

            # if the quit date is in the future, it has been reset
            # during the relapse dialog
            if quit_date > current_date:
                # if a new quit date has been set, the weekly reflection might be rescheduled,
                # a notification on the day before and on the new date are planned.
                # Then we go back to the buffer state
                reschedule_weekly_reflection(self.user_id, quit_date)
                plan_new_date_notifications(self.user_id, quit_date)
                self.set_new_state(BufferState(self.user_id))

            else:
                # if the quit date has not been changed, we go back to execution
                logging.info('Relapse completed, back to execution')
                self.set_new_state(ExecutionRunState(self.user_id))

    def on_dialog_expired(self, dialog):
        logging.info('A dialog has expired  %s ', dialog)
        # if the relapse dialog expires in a branch different from the Relapse,
        # it should not be reproposed to the user.
        if (dialog == Components.RELAPSE_DIALOG
                and get_hrs_last_branch(self.user_id) != Components.RELAPSE_DIALOG_RELAPSE):

            store_completed_dialog(user_id=self.user_id,
                                   dialog=dialog,
                                   phase_id=3)

            # let the fms know that the dialog is considered as not running anymore
            update_fsm_dialog_running_status(self.user_id, False)
            # go back to the execution
            logging.info('Relapse completed, back to execution')
            self.set_new_state(ExecutionRunState(self.user_id))

        else:
            # get the preferred time of the user and use it. Just add a day otherwise
            _, preferred_time = get_preferred_date_time(self.user_id)

            next_day = datetime.now()
            if preferred_time is not None:
                next_day.replace(hour=preferred_time.hour, minute=preferred_time.minute)

            next_day += timedelta(days=1)

            self.celery.send_task(RESCHEDULE_DIALOG,
                                  (self.user_id,
                                   dialog,
                                   next_day))

    def on_user_trigger(self, dialog: str):
        if dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=3)


class ClosingState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.CLOSING

    def run(self):
        logging.info("Running state %s", self.state)
        save_fsm_state_in_db(self.user_id, self.state)
        # plan the execution of the closing dialog

        closing_date = get_next_planned_date(
            user_id=self.user_id,
            current_date=datetime.now()
        )

        planned_date = create_new_date(closing_date)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.CLOSING_DIALOG,
                       planned_date=planned_date,
                       phase_id=2)

    def on_user_trigger(self, dialog):
        if dialog == Components.CONTINUE_UNCOMPLETED_DIALOG:
            run_uncompleted_dialog(self.user_id)
        else:
            plan_and_store(user_id=self.user_id,
                           dialog=dialog,
                           phase_id=2)

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        store_completed_dialog(user_id=self.user_id,
                               dialog=dialog,
                               phase_id=2)

        if dialog == Components.CLOSING_DIALOG:
            logging.info('Closing dialog completed. Intervention finished')
            self.set_new_state(CompletedState(self.user_id))

    def on_dialog_rescheduled(self, dialog, new_date):
        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=2)


class CompletedState(State):

    def __init__(self, user_id):
        super().__init__(user_id, celery)
        self.user_id = user_id
        self.state = State.COMPLETED

    def run(self):
        logging.info("Running state %s", self.state)
        save_fsm_state_in_db(self.user_id, self.state)

    def on_user_trigger(self, dialog):
        return
