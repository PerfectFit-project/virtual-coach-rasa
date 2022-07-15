import logging

import requests
from celery import Celery
from dateutil import tz
from utils import *
from virtual_coach_db.helper.definitions import Phases

REDIS_URL = os.getenv('REDIS_URL')

TIMEZONE = tz.gettz("Europe/Amsterdam")

app = Celery('celery_tasks', broker=REDIS_URL)

app.conf.enable_utc = True
app.conf.timezone = TIMEZONE


@app.task
def intervention_component_completed(user_id: int, intervention_component_name: str):
    phase = get_current_phase(user_id)
    intervention_component = get_intervention_component(intervention_component_name)
    intervention_component_id = intervention_component.intervention_component_id

    next_intervention_component = None

    if phase.phase_name == Phases.PREPARATION:

        store_intervention_component_to_db(user_id=user_id,
                                           intervention_phase_id=phase.phase_id,
                                           intervention_component_id=intervention_component_id,
                                           completed=True,
                                           last_time=datetime.now().astimezone(TIMEZONE))

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
            plan_execution_dialogs(user_id)

    elif phase.phase_name == Phases.EXECUTION:

        trigger = intervention_component.intervention_component_trigger
        next_planned_date = get_next_planned_date(user_id, intervention_component_id)

        # schedule the task
        task_uuid = trigger_intervention_component.apply_async(
                                                               args=[user_id, trigger],
                                                               eta=next_planned_date)

        store_intervention_component_to_db(user_id=user_id,
                                           intervention_phase_id=phase.phase_id,
                                           intervention_component_id=intervention_component_id,
                                           completed=True,
                                           last_time=datetime.now().astimezone(TIMEZONE),
                                           next_planned_date=next_planned_date,
                                           task_uuid=str(task_uuid))


@app.task
def reschedule_dialog(user_id: int, intervention_component_name: str, new_date: datetime):

    intervention_component = get_intervention_component(intervention_component_name)
    intervention_component_id = intervention_component.intervention_component_id

    phase = get_current_phase(user_id)

    # schedule the task
    task_uuid = trigger_intervention_component.apply_async(
        args=[user_id, intervention_component.trigger],
        eta=new_date)

    last_state = get_last_component_state(user_id, intervention_component_id)

    store_intervention_component_to_db(user_id=user_id,
                                       intervention_phase_id=phase.phase_id,
                                       intervention_component_id=intervention_component_id,
                                       completed=False,
                                       last_time=last_state.last_time,
                                       last_part=last_state.last_part,
                                       next_planned_date=new_date,
                                       task_uuid=str(task_uuid))

@app.task(bind=True)
def trigger_intervention_component(self, user_id, trigger): # pylint: disable=unused-argument
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
    headers = {'Content-Type': 'application/json'}
    params = {'output_channel': 'niceday_input_channel'}
    data = '{"name": "' + trigger + '" }'
    requests.post(endpoint, headers=headers, params=params, data=data)


def plan_execution_dialogs(user_id: int):
    """
        Get the preferences of a user and plan the execution of
         all the intervention components
    """
    session = get_db_session(db_url=DATABASE_URL)

    preferences = (
        session.query(UserPreferences)
        .filter(UserPreferences.users_nicedayuid == user_id)
        .all()
    )

    for preference in preferences:
        intervention_component_id = preference.intervention_component_id
        trigger = preference.intervention_component.intervention_component_trigger
        next_planned_date = get_next_planned_date(user_id, intervention_component_id)

        # schedule the task
        task_uuid = trigger_intervention_component.apply_async(
                                                               args=[user_id, trigger],
                                                               eta=next_planned_date)

        # update the DB
        store_intervention_component_to_db(user_id=user_id,
                                           intervention_phase_id=2,
                                           intervention_component_id=intervention_component_id,
                                           completed=False,
                                           next_planned_date=next_planned_date,
                                           task_uuid=str(task_uuid))