import logging
from state_machine import utils
from celery import Celery
from datetime import date, datetime, timedelta
from dateutil import tz
from state_machine.state import State
from virtual_coach_db.helper.definitions import (ComponentsTriggers,
                                                 Components, Notifications,
                                                 NotificationsTriggers)
import os

# intervention times (days)
FUTURE_SELF_INTRO = 8
GOAL_SETTING = 9
TRACKING_DURATION = 10
PREPARATION_GA = 14
MAX_PREPARATION_DURATION = 21
EXECUTION_DURATION = 12 * 7  # 12 weeks
#

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
TIMEZONE = tz.gettz("Europe/Amsterdam")
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
                           dialog=Components.PROFILE_CREATION,
                           trigger=ComponentsTriggers.PROFILE_CREATION)

        elif dialog == Components.PROFILE_CREATION:
            logging.info('Profile creation completed, starting med talk')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.MEDICATION_TALK,
                           trigger=ComponentsTriggers.MEDICATION_TALK)

        elif dialog == Components.MEDICATION_TALK:
            logging.info('Med talk completed, starting track behavior')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.TRACK_BEHAVIOR,
                           trigger=ComponentsTriggers.TRACK_BEHAVIOR)
            # notifications for tracking have to be activated
            self.schedule_tracking_notifications()

        elif dialog == Components.TRACK_BEHAVIOR:
            logging.info('Tack behavior completed, starting future self')
            plan_and_store(user_id=self.user_id,
                           dialog=Components.FUTURE_SELF,
                           trigger=ComponentsTriggers.FUTURE_SELF)

        elif dialog == Components.FUTURE_SELF:
            self.schedule_next_dialogs()
            # upon the completion of the future self dialog,
            # the new state can be triggered
            self.set_new_state(TrackingState(self.user_id))

    def on_user_trigger(self, dialog):
        # in the preparation phase nothing can be triggered
        # the central fallback mode is triggered instead
        plan_and_store(user_id=self.user_id,
                       dialog=Components.FIRST_AID_KIT,
                       trigger=ComponentsTriggers.FIRST_AID_KIT)

        return None

    def run(self):
        logging.info('Onboarding State running')
        # the first dialog is the introduction video
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id,
                          ComponentsTriggers.PREPARATION_INTRODUCTION))

    def schedule_next_dialogs(self):

        start_date = utils.get_start_date(self.user_id)

        # on day 9 at 10 a.m. send future self
        fs_time = create_new_date(start_date=start_date,
                                  time_delta=FUTURE_SELF_INTRO,
                                  hour=10)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.FUTURE_SELF,
                       trigger=ComponentsTriggers.FUTURE_SELF,
                       planned_date=fs_time)

        # on day 10 at 10 a.m. send future self plan goal setting
        gs_time = create_new_date(start_date=start_date,
                                  time_delta=GOAL_SETTING,
                                  hour=10)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.GOAL_SETTING,
                       trigger=ComponentsTriggers.GOAL_SETTING,
                       planned_date=gs_time)

    def schedule_tracking_notifications(self):
        """
        Schedule the notifications from the day after the tracking dialog completions
        to day 9 of the preparation phase
        """
        first_date = date.today() + timedelta(days=1)
        last_date = utils.get_start_date(self.user_id) + timedelta(days=8)

        for day in range((last_date - first_date).days):
            planned_date = create_new_date(start_date=first_date,
                                           time_delta=day,
                                           hour=10)

            plan_and_store(user_id=self.user_id,
                           dialog=Components.TRACK_NOTIFICATION,
                           trigger=ComponentsTriggers.TRACK_NOTIFICATION,
                           planned_date=planned_date)


class TrackingState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.user_id = user_id
        self.state = State.TRACKING
        self.new_state = None

    def run(self):
        logging.info('Starting Tracking state')
        current_date = date.today()
        self.check_if_end_date(current_date)

    def on_user_trigger(self, dialog):
        # in the preparation phase nothing can be triggered
        # the central fallback mode is triggered instead
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id,
                          ComponentsTriggers.FIRST_AID_KIT))

    def on_new_day(self, current_date: datetime.date):
        self.check_if_end_date(current_date)

    def check_if_end_date(self, date_to_check: date):
        intervention_day = utils.retrieve_intervention_day(self.user_id, date_to_check)
        # the Goal Setting state starts on day 10 of the intervention
        if intervention_day == TRACKING_DURATION:
            self.set_new_state(GoalsSettingState(self.user_id))


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
                           dialog=Components.FIRST_AID_KIT,
                           trigger=ComponentsTriggers.FIRST_AID_KIT)
            # after the completion of the goal setting dialog, the execution
            # phase can be planned
            self.plan_buffer_phase_dialogs()
        elif dialog == Components.FIRST_AID_KIT:
            logging.info('First aid kit completed, starting buffering state')
            self.set_new_state(BufferState(self.user_id))

    def plan_buffer_phase_dialogs(self):
        quit_date = utils.get_quit_date(self.user_id)
        start_date = utils.get_start_date(self.user_id)

        if (quit_date - start_date).days >= PREPARATION_GA:
            planned_date = create_new_date(start_date=start_date, time_delta=PREPARATION_GA, hour=10)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           trigger=ComponentsTriggers.GENERAL_ACTIVITY,
                           planned_date=planned_date)

        if (quit_date - start_date).days == MAX_PREPARATION_DURATION:
            planned_date = create_new_date(start_date=start_date, time_delta=MAX_PREPARATION_DURATION, hour=10)
            plan_and_store(user_id=self.user_id,
                           dialog=Components.GENERAL_ACTIVITY,
                           trigger=ComponentsTriggers.GENERAL_ACTIVITY,
                           planned_date=planned_date)

    def plan_execution_start_dialog(self):
        # this is the intro video to be sent the first time
        # the execution starts (not after lapse/relapse)
        quit_date = utils.get_quit_date(self.user_id)
        planned_date = create_new_date(quit_date, 0, 10)

        plan_and_store(user_id=self.user_id,
                       dialog=Components.EXECUTION_INTRODUCTION,
                       trigger=ComponentsTriggers.EXECUTION_INTRODUCTION,
                       planned_date=quit_date)

    def activate_pa_notifications(self):
        # the notifications start from the dey after the goal setting dialog has been completed
        # and go on every day until the end of the intervention. The intervention end date
        # is 12 weeks from the quit date.
        first_date = date.today() + timedelta(days=1)

        # the time span to quit date
        buffer_length = utils.get_quit_date(self.user_id) - first_date

        total_duration = buffer_length + EXECUTION_DURATION
        last_date = first_date + timedelta(days=total_duration)

        for day in range((last_date - first_date).days):
            planned_date = create_new_date(start_date=first_date,
                                           time_delta=day,
                                           hour=10)

            plan_and_store(user_id=self.user_id,
                           dialog=Components.PA_NOTIFICATION,
                           trigger=ComponentsTriggers.PA_NOTIFICATION,
                           planned_date=planned_date)

    def run(self):
        print(self.state)


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
        utils.store_scheduled_dialog(user_id=self.user_id,
                                     dialog=dialog,
                                     phase_id=1)

    def check_if_end_date(self, current_date: datetime.date):
        quit_date = utils.get_start_date(self.user_id)
        if current_date == quit_date:
            logging.info('Buffer sate ended, starting execution state')
            self.set_new_state(ExecutionRunState(self.user_id))


class ExecutionRunState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.state = State.EXECUTION_RUN

    def run(self):
        print(self.state)


class RelapseState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.state = State.RELAPSE

    def run(self):
        print(self.state)


class ClosingState(State):

    def __init__(self, user_id):
        super().__init__(user_id)
        self.state = State.CLOSING

    def run(self):
        print(self.state)


def create_new_date(start_date: date, time_delta: int, hour: int, minute: int = 00) -> datetime:
    """
    Create a new timedate object from the date object. It adds a 'time_delta'
    number of days to the starting date

    Args:
        start_date: the date to start from
        time_delta: the number of days to be added to the start_date
        hour: the hour to be used in the new date
        minute: the minute to be used in the new date

    Returns:
        A datetime object with the start_date + time_delta number of days and the
        hour specified

    """
    new_date = start_date + timedelta(days=time_delta)
    new_timedate = datetime(new_date.year, new_date.month, new_date.day, hour, minute)

    return new_timedate


def plan_and_store(user_id: int, dialog: str, trigger: str, planned_date: datetime = None):
    """
    Program a celery task for the planned_date, or sends it immediately in case planned_date is None,
    and stores the new component to the DB
    Args:
        user_id:user id
        dialog: dialog to be triggered
        trigger: trigger of the dialog
        planned_date: date when the dialog has to be triggered
    Returns:

    """
    if planned_date is None:
        celery.send_task(TRIGGER_COMPONENT, (user_id, trigger), eta=planned_date)

        utils.store_scheduled_dialog(user_id=user_id, dialog=dialog, phase_id=1)
    else:
        task = celery.send_task(TRIGGER_COMPONENT,
                                (user_id, trigger),
                                eta=planned_date)

        utils.store_scheduled_dialog(user_id=user_id,
                                     dialog=dialog,
                                     phase_id=1,
                                     planned_date=planned_date,
                                     task_uuid=str(task.task_id))
