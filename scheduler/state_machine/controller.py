import logging

from celery import Celery
from datetime import date, datetime, timedelta
from state_machine.state import State
from virtual_coach_db.helper.definitions import (ComponentsTriggers,
                                                 Components,
                                                 NotificationsTriggers)
from virtual_coach_db.helper.helper_functions import (get_db_session)
from virtual_coach_db.dbschema.models import Users
import os

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
celery = Celery(broker=REDIS_URL)


class OnboardingState(State):

    def __init__(self, user_id: int):
        super().__init__()
        self.state = State.ONBOARDING
        self.user_id = user_id

    def on_event(self, event):
        if event == State.TEST:
            return TrackingState()

        return self.state

    def on_dialog_completed(self, dialog):
        logging.info('A dialog has been completed')
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

    def on_user_trigger(self, dialog):
        # in the preparation phase nothing can be triggered
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id,
                          ComponentsTriggers.FIRST_AID_KIT))

    def run(self):
        logging.info('Onboarding State running')
        # the first dialog is the introduction video
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id,
                          ComponentsTriggers.PREPARATION_INTRODUCTION))

    def schedule_next_dialogs(self):

        start_date = get_start_date(self.user_id)

        # on day 9 at 10 a.m. send future self
        fs_date = start_date + timedelta(days=8)
        fs_time = datetime(fs_date.year, fs_date.month, fs_date.day, 10, 00)

        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id, ComponentsTriggers.FUTURE_SELF),
                         eta=fs_time)

        # on day 10 at 10 a.m. send future self plan goal setting
        gs_date = start_date + timedelta(days=9)
        gs_time = datetime(gs_date.year, gs_date.month, gs_date.day, 10, 00)
        celery.send_task(TRIGGER_COMPONENT,
                         (self.user_id, ComponentsTriggers.GOAL_SETTING),
                         eta=gs_time)

    def schedule_tracking_notifications(self):
        """
        Schedule the notifications from the day after the tracking dialog completions
        to day 9 of the preparation phase
        """
        first_date = date.today() + timedelta(days=1)
        last_date = get_start_date(self.user_id) + timedelta(days=8)

        for day in range((last_date - first_date).days):
            celery.send_task(TRIGGER_COMPONENT,
                             (self.user_id, NotificationsTriggers.TRACK_NOTIFICATION),
                             eta=datetime(first_date.year,
                                          first_date.month,
                                          first_date.day,
                                          10, 00) + timedelta(days=day))


class TrackingState(State):

    def __init__(self):
        super().__init__()
        self.state = State.TRACKING

    def on_event(self, event):
        if event == State.TEST:
            return GoalsSettingState()

        return self.state

    def run(self):
        print(self.state)


class GoalsSettingState(State):

    def __init__(self):
        super().__init__()
        self.state = State.GOALS_SETTING

    def on_event(self, event):
        if event == State.TEST:
            return BufferState()

        return self.state

    def run(self):
        print(self.state)


class BufferState(State):

    def __init__(self):
        super().__init__()
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


def get_start_date(user_id: int) -> date:
    """
    Retrieve teh starting date of the intervention for a user
    Args:
        user_id: ID of the user

    Returns: the intervention starting date

    """
    session = get_db_session(DATABASE_URL)

    selected = (
        session.query(
            Users
        )
        .filter(
            Users.nicedayuid == user_id
        )
        .all()
    )

    start_date = selected[0].start_date.date()

    return start_date
