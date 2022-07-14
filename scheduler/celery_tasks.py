import logging
import os

import requests
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, date, timedelta
from dateutil import tz
from virtual_coach_db.dbschema.models import (Users, UserInterventionState,
                                              InterventionPhases, InterventionComponents)
from virtual_coach_db.helper.helper_functions import get_db_session
from virtual_coach_db.helper.definitions import (Phases, PreparationInterventionComponents,
                                                 PreparationInterventionComponentsTriggers,
                                                 ExecutionInterventionComponents,
                                                 ExecutionInterventionComponentsTriggers)

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')

TIMEZONE = tz.gettz("Europe/Amsterdam")

app = Celery('celery_tasks', broker=REDIS_URL)

app.conf.enable_utc = True
app.conf.timezone = TIMEZONE

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


@app.task
def intervention_component_completed(user_id: int, intervention_component_name: str):
    phase = get_current_phase(user_id)
    intervention_component_id = get_intervention_component_id(intervention_component_name)
    store_intervention_component_to_db(user_id, phase.phase_id, intervention_component_id, True)

    next_intervention_component = None

    if phase.phase_name == Phases.PREPARATION:
        next_intervention_component = \
            get_next_preparation_intervention_component(intervention_component_name)

        if next_intervention_component is not None:
            endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
            headers = {'Content-Type': 'application/json'}
            params = {'output_channel': 'niceday_input_channel'}
            data = '{"name": "' + next_intervention_component + '" }'
            requests.post(endpoint, headers=headers, params=params, data=data)

        else:
            logging.info("PREPARATION PHASE ENDED")
            # TODO: implement execution phase dialogs scheduling
            planned_date = datetime.now() + timedelta(minutes=2)
            task_uuid = trigger_intervention_component.apply_async(
                args=[user_id,
                      PreparationInterventionComponentsTriggers.PROFILE_CREATION.value],
                eta=planned_date)
            print(task_uuid)
            app.control.revoke(str(task_uuid))
            #schedule_intervention_component_execution(user_id, datetime.now(), 'daily')


@app.task(bind=True)
def trigger_intervention_component(self, user_id, trigger): # pylint: disable=unused-argument
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
    headers = {'Content-Type': 'application/json'}
    params = {'output_channel': 'niceday_input_channel'}
    data = '{"name": "' + trigger + '" }'
    requests.post(endpoint, headers=headers, params=params, data=data)


@app.task(bind=True)
def trigger_ask_foreseen_hrs(self):  # pylint: disable=unused-argument
    """Task to trigger RASA to set reminder for every user.
    """
    # TODO: add Celery or http error handling
    user_ids = get_user_ids()
    for user in user_ids:
        endpoint = f'http://rasa_server:5005/conversations/{user}/trigger_intent'
        headers = {'Content-Type': 'application/json'}
        params = {'output_channel': 'niceday_input_channel'}
        data = '{"name": "EXTERNAL_trigger_ask_foreseen_hrs"}'
        requests.post(endpoint, headers=headers, params=params, data=data)


def get_user_ids():
    """
    Get user ids of all existing users in the database
    TODO: Add filters, i.e. active users or in a specific phase of intervention.
    """
    session = get_db_session(DATABASE_URL)
    users = session.query(Users).all()
    return [user.nicedayuid for user in users]


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


def schedule_intervention_component_execution(user_id: int):
    """
        Get the preferences of a user and plan the execution of
         an intervention component
         N.B. ATM this is just a dummy to test the functionality,
            it triggers the profile creation intervention component one minute after the request
        TODO: Check DB to get the preferences, schedule all intervention components accordingly
    """
    if recurrence is not None:
        if recurrence == 'daily':
            schedule = crontab(minute=date.minute,
                               hour=date.hour)
        elif recurrence == 'weekly':
            schedule = crontab(minute=date.minute,
                               hour=date.hour,
                               day_of_week=date.isoweekday())
        else:
            raise NameError('Recurrence type not found')
    else:
        trigger_intervention_component.apply_async(
            args=[user_id,
                  PreparationInterventionComponentsTriggers.PROFILE_CREATION.value],
            eta=date)


def store_intervention_component_to_db(user_id: int,
                                       intervention_phase_id: int,
                                       intervention_component_id: int,
                                       completed: bool):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    next_planned_date = get_next_planned_date(user_id, intervention_component_id)

    entry = UserInterventionState(intervention_phase_id=intervention_phase_id,
                                  intervention_component_id=intervention_component_id,
                                  completed=completed,
                                  last_time=datetime.now().astimezone(TIMEZONE),
                                  last_part=0,
                                  nenext_planned_date = next_planned_date)

    selected.user_intervention_state.append(entry)

    session.commit()  # Update database


def get_all_intervention_components() -> list:
    """
       Get the list of ids of all the intervention components.
    """
    session = get_db_session(DATABASE_URL)

    components = (
        session.query(
            InterventionComponents
        )
        .all()
    )

    return [component.intervention_component_id for component in components]


def get_intervention_component_id(intervention_component_name: str) -> int:
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

    intervention_component_id = selected[0].intervention_component_id
    return intervention_component_id


def get_next_planned_date(user_id: int, intervention_component_id: int) -> datetime:
    session = get_db_session(DATABASE_URL)
    selected = (
        session.query(
            UserPreferences
        )
        .filter(
            UserPreferences.users_nicedayuid == user_id,
            UserPreferences.intervention_component_id == intervention_component_id
        )
        .all()
    )

    days_str = selected.week_days
    days_list = list(map(int, days_str.split(',')))

    preferred_time = UserPreferences.preferred_time

    next_day = compute_next_day(days_list)

    next_planned_date = datetime.combine(next_day, preferred_time)

    return next_planned_date


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
