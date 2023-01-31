import logging
from state_machine import utils
from celery import Celery
from datetime import date, datetime, timedelta
from dateutil import tz
from state_machine.state import State, StateEvent
from virtual_coach_db.helper.definitions import (ComponentsTriggers,
                                                 Components,
                                                 NotificationsTriggers)
from virtual_coach_db.helper.helper_functions import (get_db_session)
from virtual_coach_db.dbschema.models import Users, UserInterventionState
import os

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
TIMEZONE = tz.gettz("Europe/Amsterdam")
celery = Celery(broker=REDIS_URL)


class OnboardingState(State):

    def __init__(self, user_id: int):
        super().__init__()
        self.state = State.ONBOARDING
        self.user_id = user_id
        self.new_state = None

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_intervention_component_to_db(user_id=self.user_id,
                                                 dialog=dialog,
                                                 phase_id=1)

        if dialog == Components.PREPARATION_INTRODUCTION:
            logging.info('Prep completed, starting profile creation')
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id,
                              ComponentsTriggers.PROFILE_CREATION))

        elif dialog == Components.PROFILE_CREATION:
            logging.info('Profile creation completed, starting med talk')
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id,
                              ComponentsTriggers.MEDICATION_TALK))

        elif dialog == Components.MEDICATION_TALK:
            logging.info('Med talk completed, starting track behavior')
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id,
                              ComponentsTriggers.TRACK_BEHAVIOR))
            # notifications for tracking have to be activated
            self.schedule_tracking_notifications()

        elif dialog == Components.TRACK_BEHAVIOR:
            logging.info('Tack behavior completed, starting future self')
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id,
                              ComponentsTriggers.FUTURE_SELF))

        elif dialog == Components.FUTURE_SELF:
            self.schedule_next_dialogs()
            # upon the completion of the future self dialog,
            # the new state can be triggered
            self.set_new_state(TrackingState(self.user_id))

    def on_user_trigger(self, dialog):
        # in the preparation phase nothing can be triggered
        # the central fallback mode is triggered instead
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id,
                          ComponentsTriggers.FIRST_AID_KIT))

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
                                  time_delta=8,
                                  hour=10)

        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id, ComponentsTriggers.FUTURE_SELF),
                         eta=fs_time)

        # on day 10 at 10 a.m. send future self plan goal setting
        gs_time = create_new_date(start_date=start_date,
                                  time_delta=9,
                                  hour=10)

        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id, ComponentsTriggers.GOAL_SETTING),
                         eta=gs_time)

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

            task = celery.send_task(TRIGGER_COMPONENT,
                                    (self.user_id, NotificationsTriggers.TRACK_NOTIFICATION),
                                    eta=planned_date)

            utils.store_scheduled_dialog(user_id=self.user_id,
                                         dialog=NotificationsTriggers.TRACK_NOTIFICATION,
                                         phase_id=1,
                                         task_uuid=str(task.task_id),
                                         planned_date=planned_date)


class TrackingState(State):

    def __init__(self, user_id):
        super().__init__()
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
        if intervention_day == 10:
            self.set_new_state(GoalsSettingState(self.user_id))


class GoalsSettingState(State):

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.state = State.GOALS_SETTING

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed  %s ', dialog)

        utils.store_intervention_component_to_db(user_id=self.user_id,
                                                 dialog=dialog,
                                                 phase_id=1)
        if dialog == Components.GOAL_SETTING:
            logging.info('Goal setting completed, starting first aid kit')
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id,
                              ComponentsTriggers.FIRST_AID_KIT))
        elif dialog == Components.FIRST_AID_KIT:
            logging.info('First aid kit completed, starting buffering state')
            self.set_new_state(BufferState(self.user_id))

    def on_new_day(self, current_date: datetime.date):
        intervention_day = utils.retrieve_intervention_day(current_date)
        if intervention_day == 14:
            self.plan_execution_phase()

    def plan_execution_phase(self):
        # TODO: add logic for exec planning
        pass

    def run(self):
        print(self.state)


class BufferState(State):

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.state = State.BUFFER

    def on_event(self, event):
        if event == State.TEST:
            return ExecutionStartState()

        return self.state

    def run(self):
        print(self.state)


class ExecutionStartState(State):

    def __init__(self):
        super().__init__()
        self.state = State.EXECUTION_START

    def on_event(self, event):
        if event == State.TEST:
            return ExecutionRunState()

        return self.state

    def run(self):
        print(self.state)


class ExecutionRunState(State):

    def __init__(self):
        super().__init__()
        self.state = State.EXECUTION_RUN

    def on_event(self, event):
        if event == State.TEST:
            return RelapseState()

        return self.state

    def run(self):
        print(self.state)


class RelapseState(State):

    def __init__(self):
        super().__init__()
        self.state = State.RELAPSE

    def on_event(self, event):
        if event == State.TEST:
            return ClosingState()

        return self.state

    def run(self):
        print(self.state)


class ClosingState(State):

    def __init__(self):
        super().__init__()
        self.state = State.RELAPSE

    def on_event(self, event):
        return self.state

    def run(self):
        print(self.state)


def create_new_date(start_date: date, time_delta: int, hour: int) -> datetime:
    """
    Create a new timedate object from the date object. It adds a 'time_delta'
    number of days to the starting date

    Args:
        start_date: the date to start from
        time_delta: the number of days to be added to the start_date
        hour: the hour to be used in the new date

    Returns:
        A datetime object with the start_date + time_delta number of days and the
        hour specified

    """
    new_date = start_date + timedelta(days=time_delta)
    new_timedate = datetime(new_date.year, new_date.month, new_date.day, hour, 00)

    return new_timedate
