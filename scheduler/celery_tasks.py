import logging
import os

import requests
from celery import Celery
from datetime import datetime, timedelta
from dateutil import tz
from virtual_coach_db.dbschema.models import (Users, UserInterventionState, InterventionPhases,
                                              InterventionComponents)
from virtual_coach_db.helper.helper import get_db_session
from virtual_coach_db.helper.definitions import Phases, PreparationDialogs, PreparationDialogsTriggers

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')

TIMEZONE = tz.gettz("Europe/Amsterdam")

app = Celery('celery_tasks', broker=REDIS_URL)

app.conf.enable_utc = True
app.conf.timezone = TIMEZONE

app.conf.beat_schedule = {
    'trigger_ask_foreseen_hrs': {
        'task': 'celery_tasks.trigger_ask_foreseen_hrs',
        'schedule': 3600.0, # every hour
        'args': (),
    },
}

@app.task
def dialog_completed(user_id: int, dialog_name: str):
    phase = get_current_phase(user_id)
    dialog_id = get_intervention_component_id(dialog_name)
    store_intervention_component_to_db(user_id, phase.phase_id, dialog_id, True)

    next_dialog = None

    if phase.phase_name == Phases.PREPARATION:
        next_dialog = get_next_preparation_dialog(dialog_name)

        if next_dialog is not None:
            endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
            headers = {'Content-Type': 'application/json'}
            params = {'output_channel': 'niceday_input_channel'}
            data = '{"name": "' + next_dialog[1] + '" }'
            requests.post(endpoint, headers=headers, params=params, data=data)

        else:
            logging.info("PREPARATION PHASE ENDED")
            # TODO: implement execution phase dialogs scheduling
            #schedule_dialog_execution(user_id)


@app.task
def trigger_dialog(user_id, trigger):
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


def get_next_preparation_dialog(dialog_id: str):
    next_dialog = 0
    if dialog_id == PreparationDialogs.PROFILE_CREATION:
        next_dialog = [PreparationDialogs.MEDICATION_TALK, PreparationDialogsTriggers.MEDICATION_TALK.value]
    if dialog_id == PreparationDialogs.MEDICATION_TALK:
        next_dialog = [PreparationDialogs.COLD_TURKEY, PreparationDialogsTriggers.COLD_TURKEY.value]
    if dialog_id == PreparationDialogs.COLD_TURKEY:
        next_dialog = [PreparationDialogs.PLAN_QUIT_START_DATE, PreparationDialogsTriggers.PLAN_QUIT_START_DATE.value]
    if dialog_id == PreparationDialogs.PLAN_QUIT_START_DATE:
        next_dialog = [PreparationDialogs.FUTURE_SELF, PreparationDialogsTriggers.FUTURE_SELF.value]
    if dialog_id == PreparationDialogs.FUTURE_SELF:
        next_dialog = [PreparationDialogs.GOAL_SETTING, PreparationDialogsTriggers.GOAL_SETTING.value]
    if dialog_id == PreparationDialogs.GOAL_SETTING:
        next_dialog = None

    return next_dialog


def schedule_dialog_execution(user_id: int):
    """
        Get the preferences of a user and plan the execution dialogs
        N.B. ATM this is just a dummy to test the functionality,
            it triggers the profile creation dialog one minute after the request
        TODO: Check DB to get the preferences, schedule all dialogs accordingly
    """
    planned_date = datetime.now() + timedelta(minutes = 1)
    print(planned_date)
    trigger_dialog.apply_async(args=[user_id, PreparationDialogsTriggers.PROFILE_CREATION.value], eta=planned_date)


def store_intervention_component_to_db(user_id: int, intervention_phase_id: int, intervention_component_id: int,
                                       completed: bool):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = UserInterventionState(intervention_phase_id =intervention_phase_id,
                                  intervention_component_id=intervention_component_id,
                                  completed=completed,
                                  last_time=datetime.now().astimezone(TIMEZONE),
                                  last_part=0)

    logging.info("db entry done")
    selected.user_intervention_state.append(entry)

    logging.info("entry added perhaps")
    session.commit()  # Update database


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
