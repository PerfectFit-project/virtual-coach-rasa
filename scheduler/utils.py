import os

from datetime import datetime, date, timedelta
from virtual_coach_db.dbschema.models import (Users, UserInterventionState, UserPreferences,
                                              InterventionPhases, InterventionComponents)
from virtual_coach_db.helper.definitions import (PreparationInterventionComponents,
                                                 PreparationInterventionComponentsTriggers)
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


def get_next_preparation_intervention_component(intervention_component_id: str):
    next_intervention_component = 0

    current_index = preparation_components_order.index(intervention_component_id)
    if current_index < len(preparation_components_order) - 1:
        next_intervention_component = preparation_triggers_order[current_index + 1]
    else:
        next_intervention_component = None

    return next_intervention_component


def get_intervention_component(intervention_component_name: str):
    """
       Get the id of an intervention component as stored in the DB
        from the intervention's name.

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


def store_intervention_component_to_db(user_id: int,
                                       intervention_phase_id: int,
                                       intervention_component_id: int,
                                       completed: bool,
                                       last_time: datetime = None,
                                       last_part: int = 0,
                                       next_planned_date: datetime = None,
                                       task_uuid: str = None):
    
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = UserInterventionState(intervention_phase_id=intervention_phase_id,
                                  intervention_component_id=intervention_component_id,
                                  completed=completed,
                                  last_time=last_time,
                                  last_part=last_part,
                                  next_planned_date=next_planned_date,
                                  task_uuid=task_uuid)

    selected.user_intervention_state.append(entry)

    session.commit()  # Update database