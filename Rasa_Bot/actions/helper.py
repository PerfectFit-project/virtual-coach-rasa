"""
Helper functions for rasa actions
"""
import datetime

from virtual_coach_db.dbschema.models import (Users, DialogAnswers)
from virtual_coach_db.helper.helper import get_db_session

from Rasa_Bot.actions.definitions import DialogQuestions, DATABASE_URL, TIMEZONE


def store_dialog_answer_to_db(user_id, answer, question: DialogQuestions):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogAnswers(answer=answer,
                          question_id=question.value,
                          datetime=datetime.datetime.now().astimezone(TIMEZONE))

    selected.dialog_answers.append(entry)
    session.commit()  # Update database
