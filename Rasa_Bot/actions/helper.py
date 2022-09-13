"""
Helper functions for rasa actions
"""
import datetime
import logging

from .definitions import DialogQuestions, DATABASE_URL, TIMEZONE
from virtual_coach_db.dbschema.models import (Users, DialogAnswers, InterventionComponents, UserPreferences)
from virtual_coach_db.helper.helper_functions import get_db_session


def store_dialog_answer_to_db(user_id, answer, question: DialogQuestions):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    logging.info("got db session")
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()
    logging.info("found user")

    entry = DialogAnswers(answer=answer,
                          question_id=question.value,
                          datetime=datetime.datetime.now().astimezone(TIMEZONE))
    logging.info("dialog answer stored to db")
    selected.dialog_answers.append(entry)
    session.commit()  # Update database

def store_user_preferences_to_db(user_id, intervention_component, recursive, week_days, preferred_time):
    logging.info("helper method started")
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    logging.info("session acquired")

    selected = session.query(Users).filter_by(nicedayuid=user_id).one()


    logging.info("established connection with DB")

    entry = UserPreferences(users_nicedayuid=user_id,
                            intervention_component_id=intervention_component,
                            recursive=recursive,
                            week_days=week_days,
                            preferred_time=preferred_time)
    logging.info("entry made successfully")
    selected.user_preferences.append(entry)
    logging.info("entry added successfully")
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

def week_day_to_numerical_form(week_day):
    logging.info(week_day.lower())
    if week_day.lower() == "monday":
        logging.info("did it")
        return 1
    elif week_day.lower() == "tuesday":
        return 2
    elif week_day.lower() == "wednesday":
        return 3
    elif week_day.lower() == "thursday":
        return 4
    elif week_day.lower() == "friday":
        return 5
    elif week_day.lower() == "saturday":
        return 6
    elif week_day.lower() == "sunday":
        return 7
    else:
        return -1