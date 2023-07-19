from datetime import date, datetime, timedelta
from sensorapi import connector
from state_machine.const import (TIMEZONE, MAXIMUM_DIALOG_DURATION, NOTIFY,
                                 NOT_RUNNING, RUNNING, EXPIRED, DATABASE_URL)
from state_machine.controller import (OnboardingState, TrackingState, GoalsSettingState,
                                      BufferState, ExecutionRunState, RelapseState, ClosingState,
                                      CompletedState)
from state_machine.state import State
from state_machine.state_machine import StateMachine, DialogState, Event
from typing import List, Optional
from virtual_coach_db.dbschema.models import (InterventionComponents, Users, UserInterventionState,
                                              UserStateMachine)
from virtual_coach_db.helper.definitions import Components, Notifications
from virtual_coach_db.helper.helper_functions import get_db_session

import logging
import numpy as np


def check_if_user_exists(user_id: int) -> bool:
    """
   Check if a user with the specified user_id exists already in the db.
    Args:
        user_id: the ID of the user
    Returns: True if the user exists, false otherwise
    """
    session = get_db_session(DATABASE_URL)

    users = (session.query(Users).filter(Users.nicedayuid == user_id).all())

    if len(users) > 0:
        return True

    return False


def check_if_user_active(user_id: int, current_date: date, days_number) -> bool:
    """
   Check if a user has been inactive (a dialog has been completed) for a certain number of days.
    Args:
        user_id: the ID of the user
        current_date: the date to start looking backward from
        days_number: number of days to check the inactivity
    Returns: True if the user has been active, false otherwise
    """
    session = get_db_session(DATABASE_URL)

    latest_date = current_date - timedelta(days=days_number)

    # get the latest completed dialog
    last_completed = (
        session.query(
            UserInterventionState
        ).order_by(UserInterventionState.last_time.desc())
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            UserInterventionState.completed.is_(True),
            UserInterventionState.last_time > latest_date
        )
        .first()
    )

    # there is at least one completed dialog in past days
    if last_completed is not None:
        return True

    return False


def check_if_physical_relapse(user_id: int, start_date: date) -> bool:
    """
    Check if a user has a physical relapse ()not reaching the stps goal.
    Args:
        user_id: the ID of the user
        start_date: the day in which to check if a relapse occurred
    Returns: True if there is a relapse, false otherwise
    """
    relapse = False

    range_end = start_date
    range_start = range_end - timedelta(days=5)

    # get the list of steps per day
    steps_taken = connector.get_steps_data(user_id, range_start, range_end)
    # if no steps have been recorded in the past 5 days
    if steps_taken is None:
        relapse = True
    # if no recordings are available for the day, or the value is lower than the threshold
    elif steps_taken[-1]['date'] != range_start or steps_taken[-1]['steps'] < 8000:
        # if there are less than 3 days with recording is the same thing as having not reached
        # the goal 4 times in 5 days
        if len(steps_taken) < 2:
            relapse = True
        else:
            # get the days where the goal has not been reached
            not_reached = [entry for entry in steps_taken if
                           entry['steps'] < get_current_steps_goal(user_id, entry['date'])]
            # if goal not reached 4 days or 3 days in a row
            if len(not_reached) >= 4 or (
                    len(not_reached) == 3 and not_reached[-1] == range_start - timedelta(days=2)):
                relapse = True

    return relapse


def check_if_task_executed(task_uuid: str) -> bool:
    """
    Check if the dialog triggered by a scheduled task has been already completed.
    In the user_intervention_state table, the tasks uuids are logged and assigned
    to the scheduled dialog they have to trigger.
    Args:
        task_uuid: the ID of the task
    Returns: True if the dialog has been already completed
    """
    session = get_db_session(DATABASE_URL)

    tasks = (session.query(UserInterventionState)
             .filter(
        UserInterventionState.task_uuid == task_uuid,
        UserInterventionState.completed.is_(False)
    )
             .all())

    if len(tasks) > 0:
        return False

    return True


def create_new_user(user_id: int):
    """
    Initialize the DB for a new user.
    Args:
        user_id: the ID of the user
    """

    # if a user exists already, print an error message
    if check_if_user_exists(user_id):
        logging.warning('User profile already in the DB')
        return

    new_user_profile = create_new_user_profile(user_id)
    new_fsm = create_new_user_fsm(user_id)

    session = get_db_session(DATABASE_URL)
    session.merge(new_user_profile)
    session.merge(new_fsm)
    session.commit()


def create_new_user_profile(user_id: int) -> Users:
    """
    Creates a new Users object for the user specified.
    Args:
        user_id: the ID of the user
    Returns: The StateMachine instance for a new user
    """

    user = Users(nicedayuid=user_id,
                 start_date=date.today())

    return user


def create_new_user_fsm(user_id: int) -> UserStateMachine:
    """
    Creates a new StateMachine for the user specified.
    Args:
        user_id: the ID of the user
    Returns: The StateMachine instance for a new user
    """
    dialog_state = DialogState(running=False,
                               starting_time=datetime.now().astimezone(TIMEZONE),
                               current_dialog=Components.PREPARATION_INTRODUCTION)

    new_fsm = StateMachine(OnboardingState(user_id), dialog_state)

    fsm_db = map_state_machine_to_db(new_fsm)

    user_fsm = get_user_fsm_from_db(user_id)

    # if a machine already exists, use the same primary key to update the row
    if user_fsm is not None:
        fsm_db.state_machine_id = user_fsm.state_machine_id

    return fsm_db


def get_all_fsm() -> List[StateMachine]:
    """
    Get the state machines as saved in the DB for all the users and maps them
    to a list of StateMachine objects

    Returns: The list of UserStateMachine objects for all the users, representing
    the user_state_machine table on the DB

       """
    fsm_list = get_all_fsm_from_db()
    state_machines = [get_user_fsm(fsm.users_nicedayuid) for fsm in fsm_list]

    return state_machines


def get_all_fsm_from_db() -> List[UserStateMachine]:
    """
       Get a list of state machines as saved in the DB for all the users. The users
       who completed the intervention are excluded.

       Returns: A list of UserStateMachine objects representing the
       user_state_machine table on the DB

       """
    session = get_db_session(DATABASE_URL)

    fsm_db = (session.query(UserStateMachine)
              .filter(UserStateMachine.state != State.COMPLETED)
              .all())

    return fsm_db


def get_component_name(intervention_component_trigger: str) -> str:
    """
    Get the intervention component name from the intervention component's trigger.

    Args:
        intervention_component_trigger: the trigger of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the Components class

    Returns:
            The intervention component name.

    """
    session = get_db_session(DATABASE_URL)

    selected = (
        session.query(
            InterventionComponents
        )
        .filter(
            InterventionComponents.intervention_component_trigger == intervention_component_trigger
        )
        .first()
    )

    return selected.intervention_component_name


def get_current_steps_goal(user_id: int, day: date) -> Optional[int]:
    """
    Get daily step goal for a given user using data from the step count database.
    For example, for a single participant, daily step count over the last 9 days (ranked from
    lowest to highest) was 1250, 1332, 3136, 5431, 5552, 5890, 6402, 7301, 10,103.
    In this case, the 60th percentile represents a goal of 5890 steps. The 6th element is used.
    If there is not data for 9 days available, the number of days will be supplemented to 9 by
    adding the average of the days with data.

    Args:
        user_id (int): The user ID for whom the daily step goal is to be retrieved from the db
    Returns:
        int: The daily step goal for the given user, retrieved from the database.
    """
    steps_per_day = []

    end = day
    start = end - timedelta(days=9)
    steps_data = connector.get_steps_data(user_id=user_id, start_date=start, end_date=end)

    for current_day in steps_data:
        steps_per_day.append(current_day['steps'])

    if len(steps_per_day) < 9:
        while len(steps_per_day) < 9:
            # Supplement with the average value up to 9 values
            steps_per_day.append(np.mean(steps_per_day))

    steps_per_day.sort()
    pa_goal = int(round(steps_per_day[5], -1))

    return pa_goal


def get_dialog_state(state_machine: StateMachine) -> int:
    """
    Gets the StateMachine object of a user
    Args:
        state_machine: Statemachine to check

    Returns: the state of the dialog: 0: not running, 1: running, 2: expired

    """
    status = state_machine.dialog_state.get_running_status()
    last_time = state_machine.dialog_state.get_running_time()

    now = datetime.now().astimezone(TIMEZONE)

    logging.info("FSM status: %s", status)
    logging.info("FSM time: %s", (now - last_time).seconds)
    logging.info("FSM id: %s", state_machine.machine_id)

    # dialog not running and completed
    if not status:
        dialog_state = NOT_RUNNING

    else:
        # dialog running and in the maximum allowed time
        if (now - last_time).seconds < MAXIMUM_DIALOG_DURATION:
            dialog_state = RUNNING
        # dialog not completed, user notified to resume the dialog
        elif (now - last_time).seconds > 2 * MAXIMUM_DIALOG_DURATION:
            dialog_state = EXPIRED
        else:
            # dialog running but the maximum time elapsed
            dialog_state = NOTIFY

    return dialog_state


def get_intervention_component(intervention_component_name: str) -> InterventionComponents:
    """
    Get the intervention component as stored in the DB from the
    intervention component's name.

    Args:
        intervention_component_name: the name of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the Components class

    Returns:
            The intervention component as an InterventionComponents object.

    """
    session = get_db_session(DATABASE_URL)

    selected = (
        session.query(
            InterventionComponents
        )
        .filter(
            InterventionComponents.intervention_component_name == intervention_component_name
        )
        .all()
    )

    return selected[0]


def get_user_fsm(user_id: int) -> StateMachine:
    """
    Get the state machine as saved in the DB for a single user and maps it
    to a StateMachine object
    Args:
        user_id: the id of the user

    Returns: The UserStateMachine object representing the user_state_machine table on the DB

    """
    fsm = get_user_fsm_from_db(user_id)

    state_saved = fsm.state
    component_saved = fsm.intervention_component

    if state_saved == State.ONBOARDING:
        state = OnboardingState(user_id)

    elif state_saved == State.TRACKING:
        state = TrackingState(user_id)

    elif state_saved == State.GOALS_SETTING:
        state = GoalsSettingState(user_id)

    elif state_saved == State.BUFFER:
        state = BufferState(user_id)

    elif state_saved == State.EXECUTION_RUN:
        state = ExecutionRunState(user_id)

    elif state_saved == State.RELAPSE:
        state = RelapseState(user_id)

    elif state_saved == State.CLOSING:
        state = ClosingState(user_id)

    elif state_saved == State.COMPLETED:
        state = CompletedState(user_id)

    else:
        state = OnboardingState(user_id)

    dialog_state = DialogState(running=fsm.dialog_running,
                               starting_time=fsm.dialog_start_time,
                               current_dialog=component_saved.intervention_component_name)

    user_fsm = StateMachine(state, dialog_state)

    return user_fsm


def get_scheduled_task_from_db() -> List[UserInterventionState]:
    """
    Get the list of all the tasks scheduled and not yet executed as they are stored in the DB.
    Returns: A list of elements of type UserInterventionState. Each element contains the scheduled
    dialog, the delivery time and the task uuid.
    """

    now = datetime.now().astimezone(TIMEZONE)

    session = get_db_session(DATABASE_URL)

    tasks = (session.query(UserInterventionState)
             .filter(
        UserInterventionState.completed.is_(False),
        UserInterventionState.task_uuid.isnot(None),
        UserInterventionState.next_planned_date.isnot(None),
        UserInterventionState.next_planned_date >= now)
             .all())

    return tasks


def get_user_fsm_from_db(user_id: int) -> UserStateMachine:
    """
    Get the state machine as saved in the DB for a single user
    Args:
        user_id: the id of the user

    Returns: The UserStateMachine object representing the user_state_machine table on the DB

    """
    session = get_db_session(DATABASE_URL)

    fsm_db = (session.query(UserStateMachine)
              .filter(UserStateMachine.users_nicedayuid == user_id)
              .first())

    return fsm_db


def map_state_machine_to_db(state_machine: StateMachine) -> UserStateMachine:
    """
    Maps a StateMachine object to the DB table object UserStateMachine
    Args:
        state_machine: StateMachine object to be mapped

    Returns: UserStateMachine object mapping the state machine

    """
    state = state_machine.state
    dialog_state = state_machine.dialog_state
    dialog = get_intervention_component(dialog_state.get_current_dialog())

    db_state_machine = UserStateMachine(users_nicedayuid=state_machine.machine_id,
                                        state=state.__state__(),
                                        dialog_running=dialog_state.get_running_status(),
                                        dialog_start_time=dialog_state.get_running_time(),
                                        intervention_component_id=dialog.intervention_component_id)

    return db_state_machine


def update_scheduled_task_db(user_id: int, task_uuid: str):
    """
    Update the last time and the completion status of a task that was triggered
    after its scheduling
    Args:
        user_id: the ID of the user to send the trigger to
        task_uuid: uuid of the task
    """
    session = get_db_session(DATABASE_URL)

    task_entry = (session.query(UserInterventionState)
                  .filter(UserInterventionState.users_nicedayuid == user_id,
                          UserInterventionState.task_uuid == task_uuid)
                  .one_or_none())

    if task_entry is None:
        return

    # update the last time value to the current time
    task_entry.last_time = datetime.now().astimezone(TIMEZONE)

    component = task_entry.intervention_component

    # if a notification has been triggered, it must be marked as completed
    # (no further interactions needed)
    values = [item.value for item in Notifications]
    if component.intervention_component_name in values:
        task_entry.completed = True

    session.commit()


def save_user_to_db(user: Users):
    """
    Saves the Users object to the database. if the user id exists, a warning is displayed.
    Args:
        user: Users object to be stored

    """
    user_id = user.nicedayuid

    # if a user exists already, print an error message
    if check_if_user_exists(user_id):
        logging.warning('User profile already in the DB')
        return

    session = get_db_session(DATABASE_URL)
    session.merge(user)
    session.commit()


def save_state_machine_to_db(state_machine: StateMachine):
    """
    Saves the StateMachine object to the database. if the user id exists,
    the record will be updated, while a new record will be created otherwise.
    Args:
        state_machine: StateMachine object to be stored

    """
    user_id = state_machine.machine_id

    fsm_db = map_state_machine_to_db(state_machine)

    user_fsm = get_user_fsm_from_db(user_id)

    # if a machine already exists, use the same primary key to update the row
    if user_fsm is not None:
        fsm_db.state_machine_id = user_fsm.state_machine_id

    session = get_db_session(DATABASE_URL)
    session.merge(fsm_db)
    session.commit()


def send_fsm_event(user_id: int, event: Event):
    """
    Send an event to the StateMachine of a user
    Args:
        user_id: ID of the user
        event: the event that need to be sent

    """

    user_fsm = get_user_fsm(user_id)

    logging.info('Event sending from celery task: %s %s', event.EventType, event.Descriptor)
    logging.info('Current machine state: %s', user_fsm.state.__state__())
    user_fsm.on_event(event)

    save_state_machine_to_db(user_fsm)


def set_dialog_running_status(user_id: int, state: bool):
    """
    Set the dialog_running status to True or False
    Args:
        user_id: ID of the user
        state: the status to be set

    """

    user_fsm = get_user_fsm(user_id)

    if state:
        current_dialog = user_fsm.dialog_state.get_current_dialog()
        user_fsm.dialog_state.set_to_running(current_dialog)
    else:
        user_fsm.dialog_state.set_to_idle()

    save_state_machine_to_db(user_fsm)


def update_task_uuid_db(old_uuid: str, new_uuid: str):
    """
    Update the uuid of a scheduled task stored in the DB to a new one
    Args:
        old_uuid: uuid already stored in the DB
        new_uuid: the uuid to be used

    """

    session = get_db_session(DATABASE_URL)

    task = (session.query(UserInterventionState)
            .filter(
        UserInterventionState.task_uuid == old_uuid
    )
            .one_or_none())

    if task is not None:
        task.task_uuid = new_uuid

        session.commit()
