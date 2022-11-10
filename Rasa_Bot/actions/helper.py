"""
Helper functions for rasa actions
"""
import datetime

from .definitions import DialogQuestions, DATABASE_URL, TIMEZONE
from virtual_coach_db.dbschema.models import (Users, DialogAnswers, InterventionComponents)
from virtual_coach_db.helper.helper_functions import get_db_session


def store_dialog_answer_to_db(user_id, answer, question: DialogQuestions):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogAnswers(answer=answer,
                          question_id=question.value,
                          datetime=datetime.datetime.now().astimezone(TIMEZONE))

    selected.dialog_answers.append(entry)
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


def get_latest_bot_utterance(events) -> str:
    events_bot = []

    for event in events:
        if event['event'] == 'bot':
            events_bot.append(event)

    last_utterance = events_bot[-1]['metadata']['utter_action']

    return last_utterance