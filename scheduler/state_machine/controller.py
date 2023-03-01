import logging
from celery import Celery
from datetime import date, datetime, timedelta
from state_machine import utils
from state_machine.const import (FUTURE_SELF_INTRO, GOAL_SETTING, TRACKING_DURATION,
                                 PREPARATION_GA, MAX_PREPARATION_DURATION, EXECUTION_DURATION,
                                 REDIS_URL, TRIGGER_COMPONENT, SCHEDULE_TRIGGER_COMPONENT)
from state_machine.state import State
from virtual_coach_db.helper.definitions import (Components, Notifications)

celery = Celery(broker=REDIS_URL)


class OnboardingState(State):

    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.state = State.ONBOARDING
        self.user_id = user_id
        self.new_state = None

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=1)

        if dialog == Components.PREPARATION_INTRODUCTION:
            logging.info('Prep completed, starting profile creation')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.PROFILE_CREATION)

        elif dialog == Components.PROFILE_CREATION:
            logging.info('Profile creation completed, starting med talk')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.MEDICATION_TALK)

        elif dialog == Components.MEDICATION_TALK:
            logging.info('Med talk completed, starting track behavior')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.TRACK_BEHAVIOR)
            # notifications for tracking have to be activated
            self.schedule_tracking_notifications()

        elif dialog == Components.TRACK_BEHAVIOR:
            logging.info('Tack behavior completed, starting future self')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.FUTURE_SELF_LONG)

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
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def run(self):
        logging.info('Onboarding State running')
        # the first dialog is the introduction video
        plan_and_store(user_id=self.user_id,
                       dialog=Components.PREPARATION_INTRODUCTION)

    def schedule_next_dialogs(self):
        # get the data on which the user has started the intervention
        # (day 1 of preparation phase)
        start_date = utils.get_start_date(self.user_id)

        # on day 9 at 10 a.m. send future self
        fs_time = utils.create_new_date(start_date=start_date,
                                        time_delta=FUTURE_SELF_INTRO)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.FUTURE_SELF_SHORT,
                       planned_date=fs_time)

    def schedule_tracking_notifications(self):
        """
        Schedule the notifications from the day after the tracking dialog completions
        to day 9 of the preparation phase
        """
        first_date = date.today() + timedelta(days=1)
        last_date = utils.get_start_date(self.user_id) + timedelta(days=8)

        for day in range((last_date - first_date).days):
            planned_date = utils.create_new_date(start_date=first_date,
                                                 time_delta=day)

            plan_and_store(user_id=self.user_id,
                           dialog=Notifications.TRACK_NOTIFICATION,
                           planned_date=planned_date)


class TrackingState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.TRACKING
        # keep track of the completion of the
        # future self dialog
        self.self_completed = False

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=1)

        if dialog == Components.FUTURE_SELF_SHORT:
            logging.info('Future self completed')
            self.self_completed = True

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_user_trigger(self, dialog):
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def run(self):
        logging.info('Starting Tracking state')

        current_date = date.today()
        self.check_if_end_date(current_date)

    def on_new_day(self, current_date: datetime.date):
        logging.info('current date: %s', current_date)

        # if it's time and the self dialog has been completed,
        # move to new state
        if (self.check_if_end_date(current_date) and
                self.self_completed):
            self.set_new_state(GoalsSettingState(self.user_id))

    def check_if_end_date(self, date_to_check: date) -> bool:
        intervention_day = utils.retrieve_intervention_day(self.user_id, date_to_check)
        # the Goal Setting state starts on day 10 of the intervention
        if intervention_day >= TRACKING_DURATION:
            return True

        return False


class GoalsSettingState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.GOALS_SETTING

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=1)

        if dialog == Components.GOAL_SETTING:
            logging.info('Goal setting completed, starting first aid kit')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.FIRST_AID_KIT_VIDEO)
            # after the completion of the goal setting dialog, the execution
            # phase can be planned
            self.plan_buffer_phase_dialogs()
            self.plan_execution_start_dialog()
            self.activate_pa_notifications()

        elif dialog == Components.FIRST_AID_KIT_VIDEO:
            logging.info('First aid kit completed, starting buffering state')
            self.set_new_state(BufferState(self.user_id))

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_user_trigger(self, dialog):
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def plan_buffer_phase_dialogs(self):
        quit_date = utils.get_quit_date(self.user_id)
        start_date = utils.get_start_date(self.user_id)

        if (quit_date - start_date).days >= PREPARATION_GA:
            planned_date = utils.create_new_date(start_date=start_date, time_delta=PREPARATION_GA)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           planned_date=planned_date)

        if (quit_date - start_date).days == MAX_PREPARATION_DURATION:
            planned_date = utils.create_new_date(start_date=start_date,
                                                 time_delta=MAX_PREPARATION_DURATION)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           planned_date=planned_date)

    def plan_execution_start_dialog(self):
        # this is the intro video to be sent the first time
        # the execution starts (not after lapse/relapse)
        quit_date = utils.get_quit_date(self.user_id)
        planned_date = utils.create_new_date(start_date=quit_date)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.EXECUTION_INTRODUCTION,
                       planned_date=planned_date)

    def activate_pa_notifications(self):
        # the notifications start from the dey after the goal setting dialog has been completed
        # and go on every day until the end of the intervention. The intervention end date
        # is 12 weeks from the quit date.
        first_date = date.today() + timedelta(days=1)

        # the time span to quit date
        buffer_length = (utils.get_quit_date(self.user_id) - first_date).days

        total_duration = buffer_length + EXECUTION_DURATION
        last_date = first_date + timedelta(days=total_duration)

        for day in range((last_date - first_date).days):
            planned_date = utils.create_new_date(start_date=first_date,
                                                 time_delta=day)

            plan_and_store(user_id=self.user_id,
                           dialog=Notifications.PA_NOTIFICATION,
                           planned_date=planned_date)

    def run(self):

        start_date = utils.get_start_date(self.user_id)

        # if the starting of this phase is after the expected one
        # launch immediately the goal setting
        if date.today() >= start_date + timedelta(days=GOAL_SETTING):
            gs_time = None

        else:
            # on day 10 at 10 a.m. send future self plan goal setting
            gs_time = utils.create_new_date(start_date=start_date,
                                            time_delta=GOAL_SETTING)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.GOAL_SETTING,
                       planned_date=gs_time)


class BufferState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.BUFFER

    def run(self):
        logging.info('Buffer State running')
        # if the user sets the quit date to the day after the goal
        # setting dialog, the buffer phase can also be immediately over
        self.check_if_end_date(date.today())

    def on_new_day(self, current_date: datetime.date):
        self.check_if_end_date(current_date)

    def on_user_trigger(self, dialog: str):
        # record that the dialog has been administered
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def check_if_end_date(self, current_date: datetime.date):
        quit_date = utils.get_quit_date(self.user_id)

        if current_date >= quit_date:
            logging.info('Buffer sate ended, starting execution state')
            self.set_new_state(ExecutionRunState(self.user_id))


class ExecutionRunState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.EXECUTION_RUN

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=2)

        if dialog == Components.EXECUTION_INTRODUCTION:
            logging.info('Execution intro completed, starting general activity')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY)

        elif dialog == Components.GENERAL_ACTIVITY:
            logging.info('General activity completed, starting weekly reflection')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.WEEKLY_REFLECTION)

        elif dialog == Components.WEEKLY_REFLECTION:
            logging.info('Weekly reflection completed')

            week = utils.get_execution_week(user_id=self.user_id)

            # if in week 3 or 8 of the execution, run future self after
            # completing the weekly reflection
            if week in [3, 8]:
                logging.info('Starting future self')
                plan_and_store(user_id=self.user_id,
                               dialog=Components.FUTURE_SELF_SHORT)

            # if in week 12, the execution is finished. Start the closing state
            elif week == 12:
                self.set_new_state(ClosingState(self.user_id))

            # in the other weeks, plan the next execution of the weekly reflection
            else:
                schedule_next_execution(user_id=self.user_id,
                                        dialog=Components.WEEKLY_REFLECTION)

        # after the completion of the future self, schedule the next weekly reflection
        elif dialog == Components.FUTURE_SELF_SHORT:
            schedule_next_execution(user_id=self.user_id,
                                    dialog=Components.WEEKLY_REFLECTION)

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)

    def on_user_trigger(self, dialog: str):

        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

        if dialog == Components.RELAPSE_DIALOG:
            self.set_new_state(RelapseState(self.user_id))

    def on_new_day(self, current_date: datetime.date):

        quit_date = utils.get_quit_date(self.user_id)

        # in case the current day of the week is the same as the one set in the
        # quit_date (and is not the same date), a new week started.
        # Thus, the execution week must be updated
        if utils.is_new_week(current_date, quit_date):
            # get the current week number
            week_number = utils.compute_spent_weeks(current_date, quit_date)

            # increase the week number by one
            utils.update_execution_week(self.user_id, week_number)

    def run(self):
        logging.info("Running state %s", self.state)


class RelapseState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.RELAPSE

    def run(self):
        logging.info("Running state %s", self.state)

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=3)

        if dialog in [Components.RELAPSE_DIALOG,
                      Components.RELAPSE_DIALOG_HRS,
                      Components.RELAPSE_DIALOG_LAPSE,
                      Components.RELAPSE_DIALOG_RELAPSE,
                      Components.RELAPSE_DIALOG_PA]:

            logging.info('Relapse dialog completed ')

            quit_date = utils.get_quit_date(self.user_id)
            current_date = date.today()

            # if the quit date is in the future, it has been reset
            # during the relapse dialog
            if quit_date > current_date:
                # if a new quit date has been set, a notification on the day before
                # and on the new date are planned. Then we go back to the buffer state
                self.plan_new_date_notifications(quit_date)
                self.set_new_state(BufferState(self.user_id))

            else:
                # if the quit date has not been changed, we go back to execution
                logging.info('Relapse completed, back to execution')
                self.set_new_state(ExecutionRunState(self.user_id))

    def on_user_trigger(self, dialog):
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def plan_new_date_notifications(self, quit_date):
        # plan the notification for the day before the quit date
        plan_and_store(user_id=self.user_id,
                       dialog=Notifications.BEFORE_QUIT_NOTIFICATION,
                       planned_date=quit_date - timedelta(days=1))

        # plan the notification for the quit date
        plan_and_store(user_id=self.user_id,
                       dialog=Notifications.QUIT_DATE_NOTIFICATION,
                       planned_date=quit_date)


class ClosingState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.CLOSING

    def run(self):
        logging.info("Running state %s", self.state)
        # plan the execution of the closing dialog

        component = utils.get_intervention_component(Components.CLOSING_DIALOG)

        closing_date = utils.get_preferred_date_time(
            user_id=self.user_id,
            intervention_component_id=component.intervention_component_id
        )[0]

        planned_date = utils.create_new_date(closing_date)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.CLOSING_DIALOG,
                       planned_date=planned_date)

    def on_user_trigger(self, dialog):
        plan_and_store(user_id=self.user_id,
                       dialog=dialog)

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_completed_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=2)

        if dialog == Components.CLOSING_DIALOG:
            logging.info('Closing dialog completed. Intervention finished')

    def on_dialog_rescheduled(self, dialog, new_date):

        reschedule_dialog(user_id=self.user_id,
                          dialog=dialog,
                          planned_date=new_date,
                          phase=1)


def plan_and_store(user_id: int, dialog: str, planned_date: datetime = None):
    """
    Program a celery task for the planned_date, or sends it immediately in case
    planned_date is None, and stores the new component to the DB
    Args:
        user_id:user id
        dialog: dialog to be triggered
        planned_date: date when the dialog has to be triggered
    Returns:

    """

    component = utils.get_intervention_component(dialog)
    dialog_id = component.intervention_component_id
    trigger = component.intervention_component_trigger

    if planned_date is None:
        celery.send_task(TRIGGER_COMPONENT, (user_id, trigger))

        utils.store_scheduled_dialog(user_id=user_id,
                                     dialog_id=dialog_id,
                                     phase_id=1)
    else:
        task = celery.send_task(SCHEDULE_TRIGGER_COMPONENT,
                                (user_id, trigger),
                                eta=planned_date)

        utils.store_scheduled_dialog(user_id=user_id,
                                     dialog_id=dialog_id,
                                     phase_id=1,
                                     planned_date=planned_date,
                                     task_uuid=str(task.task_id))


def reschedule_dialog(user_id: int, dialog: str, planned_date: datetime, phase: int):
    """
    Program a new celery task for the planned_date and store the info in the db
    Args:
        user_id:user id
        dialog: dialog to be triggered
        planned_date: date when the dialog has to be triggered
        phase: db id of the phase
    Returns:

    """
    component = utils.get_intervention_component(dialog)
    dialog_id = component.intervention_component_id
    trigger = component.intervention_component_trigger

    task = celery.send_task(SCHEDULE_TRIGGER_COMPONENT,
                            (user_id, trigger),
                            eta=planned_date)

    utils.store_rescheduled_dialog(user_id=user_id,
                                   dialog_id=dialog_id,
                                   phase_id=phase,
                                   planned_date=planned_date,
                                   task_uuid=str(task.task_id))


def schedule_next_execution(user_id: int, dialog: str):
    """
    Get the next expected execution date for an intervention component,
    and schedules it
    Args:
        user_id: id of the user
        dialog: Name of the component

    """
    component = utils.get_intervention_component(dialog)
    component_id = component.intervention_component_id

    planned_date = utils.get_next_planned_date(user_id=user_id,
                                               intervention_component_id=component_id)

    new_date = planned_date.replace(hour=10, minute=00)

    plan_and_store(user_id=user_id,
                   dialog=dialog,
                   planned_date=new_date)
