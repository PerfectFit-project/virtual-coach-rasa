import logging
import os
import requests
from celery import Celery
from datetime import datetime
from dateutil import tz
from state_machine import utils
from state_machine.state_machine import StateMachine, EventEnum, Event
from state_machine.controller import OnboardingState
from virtual_coach_db.dbschema.models import UserPreferences, UserInterventionState
from virtual_coach_db.helper.definitions import Phases, Components
from virtual_coach_db.helper.helper_functions import get_db_session

DATABASE_URL = os.getenv('DATABASE_URL')
REDIS_URL = os.getenv('REDIS_URL')

TIMEZONE = tz.gettz("Europe/Amsterdam")

app = Celery('celery_tasks', broker=REDIS_URL)

app.conf.enable_utc = True
app.conf.timezone = TIMEZONE

TEST_USER = int(os.getenv('TEST_USER_ID'))

state_machines = [{'machine': StateMachine(OnboardingState(TEST_USER)), 'id': TEST_USER}]


@app.task
def crate_new_user(user_id: int):
    global state_machines

    state_machines.append({'machine': StateMachine(OnboardingState(user_id)), 'id': user_id})


@app.task(bind=True)
def user_trigger_dialog(self,
                        user_id: int,
                        triggered_dialog: Components):  # pylint: disable=unused-argument
    send_fsm_event(user_id=user_id, event=Event(EventEnum.USER_TRIGGER, triggered_dialog))


@app.task(bind=True)
def intervention_component_completed(self,
                                     user_id: int,
                                     completed_dialog: Components):  # pylint: disable=unused-argument

    logging.info('Celery received a dialog completion')
    send_fsm_event(user_id=user_id, event=Event(EventEnum.DIALOG_COMPLETED, completed_dialog))


@app.task
def relapse_dialog(user_id: int, intervention_component_name: str):
    ##TODO functionality to detect relapse and return to correct component
    logging.info("celery received")
    phase = utils.get_phase_object(Phases.LAPSE.value)
    component = utils.get_intervention_component(intervention_component_name)

    logging.info("celery received the message")

    state = UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phase.phase_id,
        intervention_component_id=component.intervention_component_id,
        completed=False,
        last_time=datetime.now().astimezone(TIMEZONE),
        last_part=0,
        next_planned_date=None,
        task_uuid=None
    )

    utils.store_intervention_component_to_db(state)

    trigger_intervention_component.apply_async(
        args=[user_id, 'EXTERNAL_relapse_dialog'])


@app.task
def reschedule_dialog(user_id: int, intervention_component_name: str, new_date: datetime):
    intervention_component = utils.get_intervention_component(intervention_component_name)
    intervention_component_id = intervention_component.intervention_component_id

    phase = utils.get_current_phase(user_id)

    # schedule the task
    task_uuid = trigger_intervention_component.apply_async(
        args=[user_id, intervention_component.intervention_component_trigger],
        eta=new_date)

    last_state = utils.get_last_component_state(user_id, intervention_component_id)

    state = UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phase.phase_id,
        intervention_component_id=intervention_component_id,
        completed=True,
        last_time=last_state.last_time,
        last_part=last_state.last_part,
        next_planned_date=new_date,
        task_uuid=str(task_uuid)
    )

    utils.store_intervention_component_to_db(state)


@app.task(bind=True)
def trigger_intervention_component(self, user_id, trigger):  # pylint: disable=unused-argument
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
    headers = {'Content-Type': 'application/json'}
    params = {'output_channel': 'niceday_trigger_input_channel'}
    data = '{"name": "' + trigger + '" }'
    requests.post(endpoint, headers=headers, params=params, data=data, timeout=60)


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
        intervention_id = preference.intervention_component_id
        trigger = preference.intervention_component.intervention_component_trigger
        next_planned_date = utils.get_next_planned_date(user_id, intervention_id)

        # schedule the task
        task_uuid = trigger_intervention_component.apply_async(
            args=[user_id, trigger],
            eta=next_planned_date)

        phase = utils.get_phase_object(Phases.EXECUTION.value)

        # update the DB
        state = UserInterventionState(
            users_nicedayuid=user_id,
            intervention_phase_id=phase.phase_id,
            intervention_component_id=intervention_id,
            completed=False,
            last_time=None,
            last_part=0,
            next_planned_date=next_planned_date,
            task_uuid=str(task_uuid)
        )
        utils.store_intervention_component_to_db(state)


def send_fsm_event(user_id: int, event: Event):
    # get the user state machine
    user_fsm = next(item for item in state_machines if item['id'] == user_id)['machine']
    user_fsm.on_event(event)