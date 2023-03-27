"""
Helper functions for rasa actions.
"""
import numpy as np
import plotly.graph_objects as go
import secrets

from datetime import datetime
from typing import List, Optional, Any


from .definitions import (AFTERNOON_SEND_TIME,
                          DATABASE_URL, EVENING_SEND_TIME,
                          MORNING_SEND_TIME, 
                          PROFILE_CREATION_CONF_SLOTS,
                          TIMEZONE)
from virtual_coach_db.dbschema.models import (Users, DialogClosedAnswers, 
                                              DialogOpenAnswers, 
                                              InterventionActivity,
                                              InterventionActivitiesPerformed,
                                              InterventionComponents,
                                              InterventionPhases,
                                              UserInterventionState,
                                              ClosedAnswers)
from virtual_coach_db.helper.helper_functions import get_db_session


def compute_godin_level(tracker) -> int:
    "Compute the Godin activity level (0-2)."
    
    godin_light = tracker.get_slot("profile_creation_godin_light_slot")
    godin_mod = tracker.get_slot("profile_creation_godin_moderate_slot")
    godin_inten = tracker.get_slot("profile_creation_godin_intensive_slot")

    godin_score = 9 * godin_inten + 5 * godin_mod + 3 * godin_light

    godin_level = 0  # insufficiently active/sedentary
    if godin_score >= 24: # 24 units or more is active
        godin_level = 2
    elif godin_score >= 14:  # 14-23 is moderately active
        godin_level = 1
 
    return godin_level


def compute_mean_cluster_similarity_ratings(tracker):
    "Compute mean similarity ratings for testimonial clusters."
    
    # First for cluster 1
    c1_1 = tracker.get_slot("profile_creation_sim_2_slot")
    c1_2 = tracker.get_slot("profile_creation_sim_4_slot")
    c1_mean = (c1_1 + c1_2) / 2
    # Next for cluster 3
    c3_1 = tracker.get_slot("profile_creation_sim_1_slot")
    c3_2 = tracker.get_slot("profile_creation_sim_3_slot")
    c3_mean = (c3_1 + c3_2) / 2
    
    return c1_mean, c3_mean


def compute_mean_confidence(tracker) -> float:
    "Compute mean confidence."
    
    # Get confidence slots from tracker
    conf = [tracker.get_slot(slot_name) for slot_name in PROFILE_CREATION_CONF_SLOTS]
    
    # Replace -1 with 0 (-1 are values people never filled in because
    # the confidence was already low for the previous amount of physical activity)
    conf = [i if not i == -1 else 0 for i in conf]
    
    # Compute average and multiply with 10 (we used a scale from 0 to 10,
    # but the database uses a scale from 0 to 100)
    conf_avg = np.mean(conf) * 10
    
    return conf_avg


def compute_preferred_time(tracker):
    "Compute a person's preferred time for intervention components."
    
    # Get preferred time
    time_slot = tracker.get_slot("profile_creation_time_slot")
    time_hour = MORNING_SEND_TIME
    if time_slot == 2:
        time_hour = AFTERNOON_SEND_TIME
    elif time_slot == 3:
        time_hour = EVENING_SEND_TIME

    # year, month, day, hour, minute, second, microsecond
    # We only care about the hours
    preferred_time = datetime(2023, 1, 1, time_hour).astimezone(TIMEZONE)
    
    return preferred_time


def store_profile_creation_data_to_db(user_id: int, godin_activity_level: int, 
                                      running_walking_pref: int, 
                                      self_efficacy_pref: float,
                                      sim_cluster_1: float, sim_cluster_3: float,
                                      participant_code: str, week_days: str,
                                      preferred_time):
    #pylint: disable=too-many-arguments
    """
    Stores profile creation data for a user in the database.

    Args:
        user_id (int): The ID of the user to store the evaluation for.
        godin_activity_level (int): Godin activity level (0,1, or 2).
        runnin_walking_pref (int): Preference for walking (0) or running (1).
        self_efficacy_pref (float): Self-efficacy for preference of walking or running
                                    (between 0 and 100).
        sim_cluster_1 (float): Mean similarity for cluster 1 (between -3 and 3).
        sim_cluster_2 (float): Mean similarity for cluster 3 (between -3 and 3).
        participant_code (str): Participant 5-character code.
        week_days (str): String with numbers of preferred days for intervention
                         (e.g., '1' for monday).
        preferred_time: Preferred time of day for intervention.
    
    Returns:
        Nothing.
    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    selected.testim_godin_activity_level = godin_activity_level
    selected.testim_running_walking_pref = running_walking_pref
    selected.testim_self_efficacy_pref = self_efficacy_pref
    selected.testim_sim_cluster_1 = sim_cluster_1
    selected.testim_sim_cluster_3 = sim_cluster_3
    selected.participant_code = participant_code
    selected.week_days = week_days
    selected.preferred_time = preferred_time
    
    session.commit()


def store_long_term_pa_goal_to_db(user_id: int, long_term_pa_goal: str):
    """
        Store a user's long-term physical activity (PA) goal in the database.

        Args:
            user_id (int): The id of the user.
            long_term_pa_goal (str): The long-term PA goal.

        Returns:
            Nothing
    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()
    selected.long_term_pa_goal = long_term_pa_goal
    session.commit()


def store_quit_date_to_db(user_id: int, quit_date: str):
    """
    Store the quit date for a user in the database.

    Args:
        user_id (int): The id of the user.
        quit_date (str): The quit date in the format 'dd-mm-yyyy'.

    Returns:
        Nothing
    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()
    selected.quit_date = datetime.strptime(quit_date, '%d-%m-%Y')
    session.commit()


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
                                datetime=datetime.now().astimezone(TIMEZONE))
    selected.dialog_closed_answers.append(entry)
    session.commit()  # Update database


def get_user_intervention_activity_inputs(user_id: int, activity_id: int):
    session = get_db_session(db_url=DATABASE_URL)

    user_inputs = (
        session.query(
            InterventionActivitiesPerformed
        )
        .filter(
            InterventionActivitiesPerformed.users_nicedayuid == user_id,
            InterventionActivitiesPerformed.intervention_activity_id == activity_id
        ).all()
    )

    return user_inputs


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
                              datetime=datetime.now().astimezone(TIMEZONE))
    selected.dialog_open_answers.append(entry)
    session.commit()  # Update database


def store_user_intervention_state(user_id: int, intervention_component: str, phase: str):
    """
    Updater the user_intervention_state table, adding a new row with the intervention_component

    Args:
        user_id: niceday user id
        intervention_component: the name of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the Components class
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
        last_time=datetime.now().astimezone(TIMEZONE),
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

def get_closed_answers(user_id: int, question_id: int) -> List[DialogClosedAnswers]:
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

def get_all_closed_answers(question_id: int) -> List[ClosedAnswers]:
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

def get_open_answers(user_id: int, question_id: int) -> List[DialogOpenAnswers]:
    """
       Get the open answer responses associated with the given user and question.
        Args:
                user_id: the user_id of the user to retrieve the answers for
                question_id: the question_id for which the answers should be retrieved

            Returns:
                    The open answers that the user has given for the question

    """
    session = get_db_session(db_url=DATABASE_URL)

    open_answers = (
        session.query(
            DialogOpenAnswers
        )
        .filter(
            DialogOpenAnswers.users_nicedayuid == user_id,
            DialogOpenAnswers.question_id == question_id
        )
        .all()
    )

    return open_answers

def count_answers(answers: List[DialogClosedAnswers],
                  closed_answer_options: List[ClosedAnswers]) -> List[int]:
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
            [answer for answer in answers if
             answer.closed_answers_id == closed_answer.closed_answers_id]
        ) for closed_answer in closed_answer_options
    ]
    return result


def add_subplot(fig, x_axis: List[str], data, figure_specifics) -> Any:
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
                   showlegend=showlegend, marker_color=color, text=y_axis),
            row=row, col=column
        )
    fig.update_yaxes(visible=False, showticklabels=False)
    # Change the bar mode
    return fig

def populate_fig(fig, question_ids, user_id: int, legends) -> Any:
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
        closed_answer_options = get_all_closed_answers(question_ids_subset[0][0])

        data = []
        for question_ids_list in question_ids_subset:
            temp_data = [0] * len(closed_answer_options)
            for question_id in question_ids_list:
                closed_answers = get_all_closed_answers(question_id)
                answers = get_closed_answers(user_id, question_id)
                temp_data = [sum(x) for x in zip(temp_data, count_answers(answers, closed_answers))]
            data.append(temp_data)

        answer_descriptions = [answer.answer_description for answer in closed_answer_options]

        figure_specifics = [legends, i + 1, 1, bool(i == 0)]
        fig = add_subplot(fig, answer_descriptions, data, figure_specifics)

    return fig