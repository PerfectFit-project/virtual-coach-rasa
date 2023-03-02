from datetime import datetime, date, timedelta
from typing import List

from state_machine.const import (DATABASE_URL, TIMEZONE, MAXIMUM_DIALOG_DURATION,
                                 NOT_RUNNING, RUNNING, EXPIRED, DATABASE_URL)
from state_machine.controller import (OnboardingState, TrackingState, GoalsSettingState,
                                      BufferState, ExecutionRunState, RelapseState, ClosingState)
from state_machine.state import State
from state_machine.state_machine import StateMachine, EventEnum, Event, DialogState
from virtual_coach_db.dbschema.models import (Users, UserInterventionState, UserPreferences,
                                              InterventionPhases, InterventionComponents,
                                              UserStateMachine)
from virtual_coach_db.helper.helper_functions import get_db_session

import logging


def compute_next_day(selectable_days: list) -> date:
    """
    Given a list of days in the week, returns the date of
    the closest future day among the ones provided in the list

    Args:
        selectable_days: a list of the week days among to search for.
                         The list is a list of int, each int represents
                         the day of the week (e.g., 1 = Monday

    Returns:
        The date of the next day available in the list, starting from
             current date.
    """
    # get the weekday number of current date
    today = datetime.today()
    today_weekday = today.isoweekday()

    selectable_days.sort()
    # get the nex usable day in the week
    available_days = [i for i in selectable_days if i > today_weekday]

    if available_days:
        # if there are available day further in the week, get the next one
        next_weekday = available_days[0]
    else:
        # if no further days are available, get the first available in the week
        next_weekday = selectable_days[0]

    # compute the date of the next selected day
    next_date = today + timedelta((next_weekday - today_weekday) % 7)

    return next_date


def create_new_date(start_date: date,
                    time_delta: int = 0,
                    hour: int = 10,
                    minute: int = 00) -> datetime:
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


def get_dialog_state(state_machine: StateMachine) -> int:
    """
    Gets the StateMachine object of a user
    Args:
        state_machine: Statemachine to check

    Returns: the state of the dialog: 0: not running, 1: running, 2: expired

    """
    status = state_machine.dialog_state.get_running_status()
    last_time = state_machine.dialog_state.get_running_time()

    now = datetime.now()

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
        else:
            # dialog running but the maximum time elapsed
            dialog_state = EXPIRED

    return dialog_state


def get_all_fsm_from_db() -> List[UserStateMachine]:
    """
       Get a list of state machines as saved in the DB for all the users

       Returns: A list of UserStateMachine objects representing the
       user_state_machine table on the DB

       """
    session = get_db_session(DATABASE_URL)

    fsm_db = (session.query(UserStateMachine).all())

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

    else:
        state = OnboardingState(user_id)

    dialog_state = DialogState(running=fsm.dialog_running,
                               starting_time=fsm.dialog_start_time,
                               current_dialog=fsm.intervention_component.intervention_component_name)

    user_fsm = StateMachine(state, dialog_state)

    return user_fsm


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


def get_last_component_state(user_id: int, intervention_component_id: int) -> UserInterventionState:
    """
    Gets the last state saved in the DB for an intervention component

    Args:
        intervention_component_id:
        user_id: the id of the user
        intervention_component_id: the id of the intervention component as
            saved in the DB

    Returns:
            The last row saved in the user_intervention_state table in the DB for the
            given user and intervention component. A UserInterventionState object is
            returned. In case no entry is found, it returns None
    """
    session = get_db_session(DATABASE_URL)

    try:
        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                UserInterventionState.intervention_component_id == intervention_component_id
            )
            .order_by(UserInterventionState.id.desc())  # order by descending id
            .limit(1)  # get only the first result
            .one()
        )
    except:
        selected = None

    return selected


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


def get_current_phase(user_id: int) -> InterventionPhases:
    """
    Get the current phase of the intervention of a user.

    Args:
        user_id: the id of the user

    Returns:
            The current intervention phase for the given user as
            an InterventionPhases object.

    """
    session = get_db_session(DATABASE_URL)

    selected = (
        session.query(
            UserInterventionState
        )
        .join(InterventionPhases)
        .filter(
            UserInterventionState.users_nicedayuid == user_id
        )
        .order_by(UserInterventionState.id.desc())  # order by descending id
        .limit(1)  # get only the first result
        .all()
    )

    phase = selected[0].phase
    return phase


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


def get_next_planned_date(user_id: int, intervention_component_id: int) -> datetime:
    """
    Get the date planned for the administration of an intervention component, considering
    the user preferences saved in the DB.

    Args:
        user_id: the id of the user
        intervention_component_id: the id of the interventions component

    Returns:
            The date planned for the execution of the component.

    """

    date_time = get_preferred_date_time(user_id=user_id,
                                        intervention_component_id=intervention_component_id)

    # first element of the tuple is the list of days
    pref_days = date_time[0]
    # second element of the tuple is the time
    pref_time = date_time[1]

    next_day = compute_next_day(pref_days)

    next_planned_date = datetime.combine(next_day, pref_time)

    return next_planned_date


def get_phase_object(phase_name: str) -> InterventionPhases:
    """
    Get the phase as stored in the DB from the phase name.

    Args:
        phase_name: the name of the intervention component.
                    The names are listed in virtual_coach_db.helper.definitions
                    in the Phases class

    Returns:
            The phase as an InterventionPhases object.

    """
    session = get_db_session(DATABASE_URL)

    phases = (
        session.query(
            InterventionPhases
        )
        .filter(
            InterventionPhases.phase_name == phase_name
        )
        .all()
    )

    return phases[0]


def get_preferred_date_time(user_id: int, intervention_component_id: int) -> tuple:
    """
    Gets the preferred day of the week and the preferred time of the day
    set by the user
    Args:
        user_id: ID of the user
        intervention_component_id: the id of the interventions component

    Returns: the list of preferred days and time

    """
    session = get_db_session(DATABASE_URL)
    preferences = (
        session.query(
            UserPreferences
        )
        .filter(
            UserPreferences.users_nicedayuid == user_id,
            UserPreferences.intervention_component_id == intervention_component_id
        )
        .one()
    )

    days_str = preferences.week_days
    days_list = list(map(int, days_str.split(',')))

    preferred_time = preferences.preferred_time.time()

    return days_list, preferred_time


def store_intervention_component_to_db(state: UserInterventionState):
    """
    Writes a new row in the user_intervention_state table in the DB.

    Args:
        state: the UserInterventionState to be written int the DB

    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=state.users_nicedayuid).one()

    entry = UserInterventionState(
        intervention_phase_id=state.intervention_phase_id,
        intervention_component_id=state.intervention_component_id,
        completed=state.completed,
        last_time=state.last_time,
        last_part=state.last_part,
        next_planned_date=state.next_planned_date,
        task_uuid=state.task_uuid
    )

    selected.user_intervention_state.append(entry)

    session.commit()  # Update database


def get_start_date(user_id: int) -> date:
    """
    Retrieve teh starting date of the intervention for a user
    Args:
        user_id: ID of the user

    Returns: the intervention starting date

    """
    session = get_db_session(DATABASE_URL)

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    start_date = selected.start_date

    return start_date


def get_quit_date(user_id: int) -> date:
    """
    Retrieve the smoking quit date of a user
    Args:
        user_id: ID of the user

    Returns: the smoking quit starting date

    """
    session = get_db_session(DATABASE_URL)

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    quit_date = selected.quit_date

    return quit_date


def get_execution_week(user_id: int) -> int:
    """
    Computes the current wek number of the execution phase
    Args:
        user_id: ID of the user

    Returns: the week number

    """

    session = get_db_session(DATABASE_URL)

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    week_number = selected.execution_week

    return week_number


def compute_spent_weeks(current_date: date, starting_date: date) -> int:
    """
    Compute the number of weeks between two dates
    Args:
        current_date: the current date
        starting_date: the date from which to start the weeks counting

    Returns: The number of weeks beetween the two dates

    """
    spent_days = (current_date - starting_date).days

    spent_weeks = spent_days // 7

    return spent_weeks


def is_new_week(current_date: date, starting_date: date) -> bool:
    """

    Args:
        current_date: the current date
        starting_date: the date which to check against with if a new
        week has started

    Returns: True if the current_date is exctly at the beginning of a
    new week, false otherwise

    """
    spent_days = (current_date - starting_date).days

    if spent_days % 7 == 0:
        return True

    return False


def update_execution_week(user_id: int, week_number: int):
    """
    Computes the current wek number of the execution phase
    Args:
        user_id: ID of the user
        week_number: execution week number

    Returns: the week number

    """
    session = get_db_session(DATABASE_URL)

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    selected.execution_week = week_number

    session.commit()


def retrieve_intervention_day(user_id: int, current_date: date) -> int:
    """
    Computes the number of days from the start day of the intervention
    (first day of preparation phase)

    Args:
        user_id: ID of the user
        current_date: the current date

    Returns:
        The number of days since  the intervention start day

    """
    start_date = get_start_date(user_id=user_id)

    # add +1 because the count starts at day 1
    intervention_day = (current_date - start_date).days + 1

    return intervention_day


def store_rescheduled_dialog(user_id: int,
                             dialog_id: int,
                             phase_id: int,
                             planned_date: datetime,
                             task_uuid: str = None):
    """
    This function marks when a dialog has been rescheduled, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog_id: db id of the dialog
        phase_id: id of the intervention phase
        planned_date: date when the dialog is to be delivered
        task_uuid: celery task uuid

    """
    # get the id of the dialog
    last_state = get_last_component_state(user_id=user_id,
                                          intervention_component_id=dialog_id)

    # update the dialog entry, setting a new date an uuid
    if last_state is not None:
        last_state.last_time = datetime.now().astimezone(TIMEZONE)
        session = get_db_session(DATABASE_URL)
        selected = (session.query(UserInterventionState)
                    .filter(UserInterventionState.id == last_state.id)
                    .one())

        selected.next_planned_date = planned_date
        selected.task_uuid = task_uuid

        session.commit()

    # if for any reason the dialog starting was not recorded in the DB, create the entry
    else:
        state = UserInterventionState(
            users_nicedayuid=user_id,
            intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
            intervention_component_id=dialog_id,
            completed=False,
            last_time=datetime.now().astimezone(TIMEZONE),
            last_part=0,
            next_planned_date=planned_date,
            task_uuid=task_uuid
        )
        # record the dialog completion in the DB
        store_intervention_component_to_db(state)


def store_completed_dialog(user_id: int, dialog: str, phase_id: int):
    """
    This function marks when a dialog has been completed, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog: name of the dialog
        phase_id: id of the intervention phase

    """
    # get the id of the dialog
    dialog = get_intervention_component(dialog)
    last_state = get_last_component_state(user_id,
                                          dialog.intervention_component_id)

    # update the dialog entry, setting the `completed` filed to true
    if last_state is not None:
        last_state.last_time = datetime.now().astimezone(TIMEZONE)
        session = get_db_session(DATABASE_URL)
        selected = (session.query(UserInterventionState)
                    .filter(UserInterventionState.id == last_state.id)
                    .one())

        selected.completed = True

        session.commit()
    # if for any reason the dialog starting was not recorded in the DB, create the entry
    else:
        state = UserInterventionState(
            users_nicedayuid=user_id,
            intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
            intervention_component_id=dialog.intervention_component_id,
            completed=True,
            last_time=datetime.now().astimezone(TIMEZONE),
            last_part=0,
            next_planned_date=None,
            task_uuid=None
        )
        # record the dialog completion in the DB
        store_intervention_component_to_db(state)


def store_scheduled_dialog(user_id: int,
                           dialog_id: int,
                           phase_id: int,
                           planned_date: datetime = datetime.now().astimezone(TIMEZONE),
                           task_uuid: str = None):
    """
    This function marks when a dialog has been completed, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog_id: db id of the dialog
        phase_id: id of the intervention phase
        planned_date: date when the dialog is to be delivered
        task_uuid: celery task uuid

    """
    # get the id of the dialog

    state = UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
        intervention_component_id=dialog_id,
        completed=False,
        last_time=None,
        last_part=0,
        next_planned_date=planned_date,
        task_uuid=task_uuid
    )
    # record the dialog completion in the DB
    store_intervention_component_to_db(state)
