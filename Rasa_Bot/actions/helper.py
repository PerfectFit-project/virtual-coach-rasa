"""
Helper functions for rasa actions
"""
import datetime
import secrets

from .definitions import DialogQuestions, DATABASE_URL, TIMEZONE
from virtual_coach_db.dbschema.models import (Users, DialogClosedAnswers, DialogOpenAnswers, InterventionComponents,
                                              UserPreferences, InterventionActivity)
from virtual_coach_db.helper.helper_functions import get_db_session


def store_dialog_closed_answer_to_db(user_id, answer_id):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogClosedAnswers(closed_answers_id=answer_id,
                                datetime=datetime.datetime.now().astimezone(TIMEZONE))
    selected.dialog_closed_answers.append(entry)
    session.commit()  # Update database


def store_dialog_open_answer_to_db(user_id, question_id, answer_value):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogClosedAnswers(question_id=question_id,
                                answer_value=answer_value,
                                datetime=datetime.datetime.now().astimezone(TIMEZONE))
    selected.dialog_closed_answers.append(entry)
    session.commit()  # Update database


def store_user_preferences_to_db(user_id, intervention_component, recursive, week_days,
                                 preferred_time):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = UserPreferences(users_nicedayuid=user_id,
                            intervention_component_id=intervention_component,
                            recursive=recursive,
                            week_days=week_days,
                            preferred_time=preferred_time)
    selected.user_preferences.append(entry)
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

    if len(events_bot) != 0:
        last_utterance = events_bot[-1]['metadata']['utter_action']
    else:
        last_utterance = None

    return last_utterance


def get_random_activities(avoid_activity_id: int, number_of_activities: int):
    session = get_db_session(db_url=DATABASE_URL)

    available_activities = (
        session.query(
            InterventionActivity
        )
        .filter(
            InterventionActivity.intervention_activity_id != avoid_activity_id
        )
        .all()
    )

    rnd_activities = []

    for _ in range(number_of_activities):
        random_choice = secrets.choice(available_activities)
        rnd_activities.append(random_choice)
        available_activities.remove(random_choice)

    return rnd_activities


def week_day_to_numerical_form(week_day):
    if week_day.lower() == "monday":
        return 1
    if week_day.lower() == "tuesday":
        return 2
    if week_day.lower() == "wednesday":
        return 3
    if week_day.lower() == "thursday":
        return 4
    if week_day.lower() == "friday":
        return 5
    if week_day.lower() == "saturday":
        return 6
    if week_day.lower() == "sunday":
        return 7
    return -1
