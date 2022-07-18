import os

from datetime import datetime, date, timedelta
from virtual_coach_db.dbschema.models import (Users, UserInterventionState, UserPreferences,
                                              InterventionPhases, InterventionComponents)
from virtual_coach_db.helper.definitions import (PreparationInterventionComponents,
                                                 PreparationInterventionComponentsTriggers,
                                                 Phases)
from virtual_coach_db.helper.helper_functions import get_db_session


DATABASE_URL = os.getenv('DATABASE_URL')


# ordered lists of the intervention components
preparation_components_order = [PreparationInterventionComponents.PROFILE_CREATION,
                                PreparationInterventionComponents.MEDICATION_TALK,
                                PreparationInterventionComponents.COLD_TURKEY,
                                PreparationInterventionComponents.PLAN_QUIT_START_DATE,
                                PreparationInterventionComponents.FUTURE_SELF,
                                PreparationInterventionComponents.GOAL_SETTING]

preparation_triggers_order = [PreparationInterventionComponentsTriggers.PROFILE_CREATION.value,
                              PreparationInterventionComponentsTriggers.MEDICATION_TALK.value,
                              PreparationInterventionComponentsTriggers.COLD_TURKEY.value,
                              PreparationInterventionComponentsTriggers.PLAN_QUIT_START_DATE.value,
                              PreparationInterventionComponentsTriggers.FUTURE_SELF.value,
                              PreparationInterventionComponentsTriggers.GOAL_SETTING.value]


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
    next_date = today + timedelta((next_weekday-today_weekday) % 7)

    return next_date


def get_last_component_state(user_id: int, intervention_component_id: int) -> UserInterventionState:
    """
    Gets the last state saved in the DB for an intervention component

    Args:
        user_id: the id of the user
            intervention_component_id: the id of the intervention component as
            saved in the DB

    Returns:
            The last row saved in the user_intervention_state table in the DB for the
            given user and intervention component. A UserInterventionState object is
            returned.
    """
    session = get_db_session(DATABASE_URL)

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
        .all()
    )

    return selected[0]


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


def get_next_preparation_intervention_component(intervention_component: str):
    """
    Get the next intervention component to be administered in the preparation
    phase, given the current completed intervention component.

    Args:
        intervention_component: the name of the currently completed component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the PreparationInterventionComponents class

    Returns:
            The next intervention component to be administered

    """
    next_intervention_component = 0

    current_index = preparation_components_order.index(intervention_component)
    if current_index < len(preparation_components_order) - 1:
        next_intervention_component = preparation_triggers_order[current_index + 1]
    else:
        next_intervention_component = None

    return next_intervention_component


def get_intervention_component(intervention_component_name: str):
    """
    Get the intervention component as stored in the DB from the
    intervention component's name.

    Args:
        intervention_component_name: the name of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the PreparationInterventionComponents class

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

    preferred_time = preferences.preferred_time

    next_day = compute_next_day(days_list)

    next_planned_date = datetime.combine(next_day, preferred_time)

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