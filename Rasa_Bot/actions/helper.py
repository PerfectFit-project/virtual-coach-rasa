"""
Helper functions for rasa actions
"""
import datetime
import secrets
from typing import List, Optional, Any
import plotly.graph_objects as go

from .definitions import DATABASE_URL, TIMEZONE
from virtual_coach_db.dbschema.models import (Users, DialogClosedAnswers, DialogOpenAnswers,
                                              InterventionComponents, UserPreferences,
                                              InterventionActivity, UserInterventionState,
                                              InterventionPhases, ClosedAnswers)
from virtual_coach_db.helper.helper_functions import get_db_session


def store_dialog_closed_answer_to_db(user_id: int, question_id: int, answer_value: int):
    """
       saves to the db a closed answer

        Args:
            user_id: niceday user id
            question_id: the id of the question. The ids are listed in
            virtual_coach_db.helper.definitions in the DialogQuestionsEnum class
            answer_value: the value chosen by the user

        Returns:
                nothing

    """
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()
    # The answers to the closed questions are pre-defined and initialized in the DB.
    # To have a unique known ID for the answers that we can use to store the user's response,
    # it is assigned by combining the question id and the value of the answer (always a number)
    # using the following logic. See also virtual_coach_db.helper.populate_db
    answer_id = answer_value + question_id * 100

    entry = DialogClosedAnswers(closed_answers_id=answer_id,
                                datetime=datetime.datetime.now().astimezone(TIMEZONE))
    selected.dialog_closed_answers.append(entry)
    session.commit()  # Update database


def store_dialog_closed_answer_list_to_db(user_id: int, question_id: int, answers_values: str):
    """
       saves to the db all the closed answers provided as a string, where each answer value
       is separated from the other by a space character

        Args:
            user_id: niceday user id
            question_id: the id of the question. The ids are listed in
            virtual_coach_db.helper.definitions in the DialogQuestionsEnum class
            answers_values: the values chosen by the user

        Returns:
                nothing

    """

    values = list(map(int, answers_values.split()))

    for item in values:
        store_dialog_closed_answer_to_db(user_id,
                                         question_id,
                                         item)


def store_dialog_open_answer_to_db(user_id: int, question_id: int, answer_value: str):
    """
       saves to the db an open answer

        Args:
            user_id: niceday user id
            question_id: the id of the question. The ids are listed in
            virtual_coach_db.helper.definitions in the DialogQuestionsEnum class
            answer_value: the value chosen by the user

        Returns:
                nothing

    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogOpenAnswers(question_id=question_id,
                              answer_value=answer_value,
                              datetime=datetime.datetime.now().astimezone(TIMEZONE))
    selected.dialog_open_answers.append(entry)
    session.commit()  # Update database


def store_user_preferences_to_db(user_id: int, intervention_component_id: int, recursive: bool,
                                 week_days: str, preferred_time: datetime.datetime):
    """
    Updater the user_intervention_state table, adding a new row with the intervention_component

    Args:
        user_id: niceday user id
        intervention_component_id: the id of the intervention component as store din the DB.
        recursive: if true the activity is recursive, and will be reprogrammed after the completion
        week_days: comma separated list of days
        preferred_time: preferred time in the day to prompt the activity

    Returns:
            nothing

    """
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = UserPreferences(users_nicedayuid=user_id,
                            intervention_component_id=intervention_component_id,
                            recursive=recursive,
                            week_days=week_days,
                            preferred_time=preferred_time)
    selected.user_preferences.append(entry)
    session.commit()  # Update database


def store_user_intervention_state(user_id: int, intervention_component: str, phase: str):
    """
    Updater the user_intervention_state table, adding a new row with the intervention_component

    Args:
        user_id: niceday user id
        intervention_component: the name of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the PreparationInterventionComponents class
        phase: the name of the phase. The names are listed in virtual_coach_db.helper.definitions
               Phases class

    Returns:
            nothing

    """
    session = get_db_session(db_url=DATABASE_URL)

    phases = (
        session.query(
            InterventionPhases
        )
        .filter(
            InterventionPhases.phase_name == phase
        )
        .all()
    )

    components = (
        session.query(
            InterventionComponents
        )
        .filter(
            InterventionComponents.intervention_component_name == intervention_component
        )
        .all()
    )

    # if the list of phases of components is empty, it is not in the DB
    if not phase or not components:
        raise ValueError('component or phase not found')

    session.add(UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phases[0].phase_id,
        intervention_component_id=components[0].intervention_component_id,
        completed=False,
        last_time=datetime.datetime.now().astimezone(TIMEZONE),
        last_part=0,
        next_planned_date=None,
        task_uuid=None
    )
    )
    session.commit()  # Update database


def get_intervention_component_id(intervention_component_name: str) -> int:
    """
       Get the id of an intervention component as stored in the DB
        from the intervention's name.
    Args:
            intervention_component_name: Name of the intervention component, as provided
            in the definitions

        Returns:
                The intervention_component_id stored in the DB
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


def get_latest_bot_utterance(events) -> Optional[Any]:
    """
       Get the latest utterance sent by the VC.
        Args:
                events: the events list, obtained from tracker.events

            Returns:
                    The name of the latest utterance

    """
    events_bot = []

    for event in events:
        if event['event'] == 'bot':
            events_bot.append(event)

    if (len(events_bot) != 0
            and 'metadata' in events_bot[-1]
            and 'utter_action' in events_bot[-1]['metadata']):
        last_utterance = events_bot[-1]['metadata']['utter_action']
    else:
        last_utterance = None

    return last_utterance


def get_random_activities(avoid_activity_id: int, number_of_activities: int
                          ) -> List[InterventionActivity]:
    """
       Get a number of random activities from the resources list.
        Args:
                avoid_activity_id: the intervention_activity_id of an activitye that
                should not be included in the list

                number_of_activities: the number of activities to be proposed

            Returns:
                    The list of number_of_activities random InterventionActivities

    """
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

def get_closed_answers(user_id, question_id):
    """
       Get the closed answer responses associated with the given user and question.
        Args:
                user_id: the user_id of the user to retrieve the answers for
                question_id: the question_id for which the answers should be retrieved

            Returns:
                    All the answers that the user has given for the given question

    """
    session = get_db_session(db_url=DATABASE_URL)

    closed_answers = (
        session.query(
            DialogClosedAnswers
        )
        .join(ClosedAnswers)
        .filter(
            DialogClosedAnswers.users_nicedayuid == user_id,
            ClosedAnswers.question_id == question_id
        )
        .all()
    )

    return closed_answers

def get_all_closed_answers(question_id):
    """
       Get all the possible closed answers associated with a given question id.
        Args:
                question_id: the question_id for which the answers should be retrieved

            Returns:
                    All the possible answers to the question specified

    """
    session = get_db_session(db_url=DATABASE_URL)

    closed_answers = (
        session.query(
            ClosedAnswers
        )
        .filter(
            ClosedAnswers.question_id == question_id
        )
        .all()
    )

    return closed_answers

def get_open_answers(user_id, question_id):
    """
       Get the open answer responses associated with the given user and question.
        Args:
                user_id: the user_id of the user to retrieve the answers for
                question_id: the question_id for which the answers should be retrieved

            Returns:
                    The open answers that the user has given for the question

    """
    session = get_db_session(db_url=DATABASE_URL)

    closed_answers = (
        session.query(
            DialogOpenAnswers
        )
        .filter(
            DialogOpenAnswers.users_nicedayuid == user_id,
            DialogOpenAnswers.question_id == question_id
        )
        .all()
    )

    return closed_answers

def count_answers(answers, closed_answer_options):
    """
       Count up the closed_answer responses for each answer option.
        Args:
                answers: the answers of the user, retreived from the database
                closed_answer_options: the answer options for the given question

            Returns:
                    An array of values, specifying the amount of occurences of an answer
                    for the corresponding option, aligning with the index of the option.
                    Example... [2, 1, 3] for ["At the gym", "At home", "Outside"]

    """
    result = [
        len(
            [answer for answer in answers if answer.closed_answers_id == closed_answer.closed_answers_id]
        ) for
              closed_answer in closed_answer_options
    ]

    return result



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

def add_subplot(fig, x_axis, data, figure_specifics):
    """
       Add a barchart subplot to a given figure, with the following data.
        Args:
                fig: the figure to add a subplot to
                x_axis: the x-axis of the added bar chart, corresponds to the answer options
                data: the actual data, these are the values returned by count_answers
                figure_specifics: minor specifications about the subplot to be added
            Returns:
                    An updated figure, with the new barchart subplot added in.
    """
    legends, row, column, showlegend = figure_specifics
    for i, y_axis in enumerate(data):
        legend, color = legends[i]
        fig.add_trace(
            go.Bar(legendgroup=legend, name=legend, x=x_axis, y=y_axis,
                   showlegend=showlegend, marker_color=color),
            row=row, col=column
        )
    # Change the bar mode
    return fig

def populate_fig(fig, question_ids, user_id, legends):
    """
       Populate a given figure with the responses for the closed answers,
       associated with the specific user.
        Args:
                fig: the figure to populate
                question_ids: the questions to retrieve the responses to
                user_id: the id of the user to retrieve the responses to
                legends: the titles and colors for the plot
            Returns:
                    A plot, showing the accumulated results for each
                    question specified by the parameters.
    """
    for i, question_ids_subset in enumerate(question_ids):
        closed_answer_options = get_all_closed_answers(question_ids_subset[0])

        data = [count_answers(get_closed_answers(user_id, question_id), get_all_closed_answers(question_id)) for
                question_id in question_ids_subset]

        answer_descriptions = [answer.answer_description for answer in closed_answer_options]

        showlegend = bool(i == 0)

        figure_specifics = [legends, i + 1, 1, showlegend]
        fig = add_subplot(fig, answer_descriptions, data, figure_specifics)

    return fig