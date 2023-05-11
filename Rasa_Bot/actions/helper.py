"""
Helper functions for rasa actions.
"""
import numpy as np
import plotly.graph_objects as go
import secrets

from datetime import datetime, date
from typing import List, Optional, Any, Tuple
from .definitions import (AFTERNOON_SEND_TIME,
                          DATABASE_URL, EVENING_SEND_TIME,
                          MORNING_SEND_TIME,
                          PROFILE_CREATION_CONF_SLOTS,
                          TIMEZONE, NUM_TOP_ACTIVITIES,
                          FsmStates)

from virtual_coach_db.dbschema.models import (Users, DialogClosedAnswers,
                                              DialogOpenAnswers,
                                              InterventionActivity,
                                              InterventionActivitiesPerformed,
                                              InterventionComponents,
                                              InterventionPhases,
                                              UserInterventionState, FirstAidKit,
                                              ClosedAnswers, UserStateMachine)
from virtual_coach_db.helper.definitions import Components
import pandas as pd

from virtual_coach_db.helper.helper_functions import get_db_session, get_timing


def compute_godin_level(tracker) -> int:
    "Compute the Godin activity level (0-2)."

    godin_light = tracker.get_slot("profile_creation_godin_light_slot")
    godin_mod = tracker.get_slot("profile_creation_godin_moderate_slot")
    godin_inten = tracker.get_slot("profile_creation_godin_intensive_slot")

    godin_score = 9 * godin_inten + 5 * godin_mod + 3 * godin_light

    godin_level = 0  # insufficiently active/sedentary
    if godin_score >= 24:  # 24 units or more is active
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
    # pylint: disable=too-many-arguments
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


def store_pf_evaluation_to_db(user_id: int, pf_evaluation_grade: int, pf_evaluation_comment: str):
    """
    Stores a performance evaluation grade and comment for a user in the database.

    Args:
        user_id (int): The ID of the user to store the evaluation for.
        pf_evaluation_grade (int): The grade of the performance evaluation, from 0 to 10.
        pf_evaluation_comment (str): The comment accompanying the performance evaluation.

    """

    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()
    selected.pf_evaluation_grade = pf_evaluation_grade
    selected.pf_evaluation_comment = pf_evaluation_comment
    session.commit()


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
        .first()
    )

    components = (
        session.query(
            InterventionComponents
        )
        .filter(
            InterventionComponents.intervention_component_name == intervention_component
        )
        .first()
    )

    # if the list of phases of components is empty, it is not in the DB
    if not phase or not components:
        raise ValueError('component or phase not found')

    session.add(UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phases.phase_id,
        intervention_component_id=components.intervention_component_id,
        completed=False,
        last_time=datetime.now().astimezone(TIMEZONE),
        last_part=0,
        next_planned_date=None,
        task_uuid=None
    )
    )
    session.commit()  # Update database


def get_activities_from_id(activity_id: int) -> InterventionActivity:
    """
    Get the InterventionActivity of an activity.
     Args:
            activity_id: the id of an activity

         Returns:
                The InterventionActivity correspondent to the activity_id

        """
    session = get_db_session(db_url=DATABASE_URL)

    activity = (
        session.query(
            InterventionActivity
        )
        .filter(
            InterventionActivity.intervention_activity_id == activity_id
        )
        .first()
    )

    return activity


def get_current_user_phase(user_id: int) -> str:
    """
       Get a number of random activities from the resources list.
        Args:
                 user_id: niceday user id

            Returns:
                    The name of the current phase of the user state machine

    """
    session = get_db_session(db_url=DATABASE_URL)

    user_fsm = (
        session.query(
            UserStateMachine
        )
        .filter(
            UserStateMachine.users_nicedayuid == user_id
        )
        .first()
    )

    return user_fsm.state


def get_current_phase_time(user_id: int, phase: str) -> int:
    """
       Get a number of random activities from the resources list.
        Args:
                 user_id: niceday user id
                 phase: current fsm state

            Returns:
                    The number of days or weeks in the current state

    """
    if phase not in [FsmStates.TRACKING, FsmStates.GOALS_SETTING, FsmStates.GOALS_SETTING]:
        time = get_days_from_start(user_id)
    else:
        time = get_execution_week(user_id)

    return time


def get_days_from_start(user_id: int) -> int:
    """
    Retrieve the number of days passed from the first day of intervention
    Args:
        user_id: ID of the user

    Returns:  number of days passed from the first day of intervention

    """
    start_date = get_start_date(user_id)

    current_date = date.today()

    spent_days = (current_date - start_date).days + 1  # if the date is the same, it is day 1

    return spent_days


def get_execution_week(user_id: int) -> int:
    """
    Retrieve the week number in the execution phase
    Args:
        user_id: ID of the user

    Returns:  number of weeks spent in the execution phase

    """
    session = get_db_session(db_url=DATABASE_URL)

    user = (
        session.query(
            Users
        )
        .filter(
            Users.nicedayuid == user_id
        )
        .first()
    )

    return user.execution_week


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
        .first()
    )

    intervention_component_id = selected.intervention_component_id
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


def get_possible_activities(user_id: int, activity_category: Optional[str] = None,
                            avoid_activity_id: Optional[int] = None
                            ) -> Tuple[List[InterventionActivity], List[InterventionActivity]]:
    """
       Get a number of random activities from the resources list.
        Args:
                user_id: ID of the user
                activity_category: category of activity to select from
                avoid_activity_id: the intervention_activity_id of an activity that
                should not be included in the list

            Returns:
                    A tuple containing a list of the mandatory activities as first element
                    and a list of the available activities as second element

    """

    timing = get_timing()
    curr_ph = get_current_user_phase(user_id)
    curr_time = get_current_phase_time(user_id, curr_ph)

    if activity_category is None:
        activities_list = list(filter(lambda x: x["resource_id"] != avoid_activity_id, timing))
    else:
        activities_list = list(filter(
            lambda x: x["category"] == activity_category and x["resource_id"] != avoid_activity_id,
            timing)
        )

    available_ids = []
    mandatory = []

    for resource in activities_list:
        if resource["always_available"]:
            available_ids.append(resource["resource_id"])
        else:
            phase = list(filter(lambda x: x["phase"] == curr_ph, resource["phases"]))
            if len(phase) > 0 and phase[0]["always_available"]:
                available_ids.append(resource["resource_id"])
            elif len(phase) > 0 and curr_time in phase[0]["available"]:
                available_ids.append(resource["resource_id"])
            # check if the current time is equal or higher than the mandatory. The user could
            # have rescheduled the dialog, so we need to take that into account. In case
            # the activity has been already performed, it is removed form the mandatory list
            if len(phase) > 0 and "mandatory" in phase[0]:
                for mandatory_time in phase[0]["mandatory"]:
                    if curr_time >= mandatory_time:
                        mandatory.append(resource["resource_id"])

    mandatory_ids = []
    # check if the mandatory activities have been already performed
    for activity in mandatory:
        # if the activity has been completed, do not report it as mandatory
        if is_activity_done(activity):
            mandatory_ids.append(activity)

    mandatory_ids = [get_activities_from_id(mandatory_id) for mandatory_id in mandatory_ids]
    available_ids = [get_activities_from_id(available_id) for available_id in available_ids]

    return mandatory_ids, available_ids


def get_intensity_minutes_goal(user_id: int) -> int:
    """
    Retrieve the current intensity minutes weekly goal of a user
    Args:
        user_id: ID of the user

    Returns: the current intensity minutes weekly goal

    """
    session = get_db_session(DATABASE_URL)

    user_info = (session.query(Users).filter(Users.nicedayuid == user_id).one())
    return user_info.pa_intensity_minutes_weekly_goal


def set_intensity_minutes_goal(user_id: int, goal: int):
    """
    Set the new intensity minutes weekly goal of a user
    Args:
        user_id: ID of the user
        goal: the new amount of intensity minutes set as a goal


    """
    session = get_db_session(DATABASE_URL)

    user_info = (session.query(Users).filter(Users.nicedayuid == user_id).one())

    user_info.pa_intensity_minutes_weekly_goal = goal

    session.commit()


def get_pa_group(user_id: int) -> int:
    """
    Retrieve the physical activity group of a user
    Args:
        user_id: ID of the user

    Returns: the pa group of the user

    """
    session = get_db_session(DATABASE_URL)

    user_info = (session.query(Users).filter(Users.nicedayuid == user_id).one())

    return user_info.pa_intervention_group


def set_pa_group(user_id: int, pa_group: int):
    """
    Set the physical activity group of a user
    Args:
        user_id: ID of the user
        pa_group: physical activity group value to be saved


    """
    session = get_db_session(DATABASE_URL)

    user_info = (session.query(Users).filter(Users.nicedayuid == user_id).one())

    user_info.pa_intervention_group = pa_group

    session.commit()


def get_start_date(user_id: int) -> date:
    """
    Retrieve teh starting date of the intervention for a user
    Args:
        user_id: ID of the user

    Returns: the intervention starting date

    """
    session = get_db_session(DATABASE_URL)

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    start_date = selected.start_date

    return start_date


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


def get_user(user_id: int) -> Users:
    """
       Get the user column in the database
        Args:
                user_id: the user_id of the user to retrieve

            Returns:
                    The user info stored in the database

    """
    session = get_db_session(db_url=DATABASE_URL)

    user_info = (
        session.query(
            Users
        )
        .filter(
            Users.nicedayuid == user_id
        )
        .one()
    )

    return user_info


def is_activity_done(activity_id: int) -> bool:
    """
    Checks if an activity has been already completed by a user
    Args:
        activity_id: id of the activity to be checked

    Returns: True if the activity has been already completed, false otherwise

    """
    session = get_db_session(db_url=DATABASE_URL)
    activities = (
        session.query(
            InterventionActivitiesPerformed
        )
        .filter(
            InterventionActivitiesPerformed.intervention_activity_id == activity_id
        ).all()
    )
    if len(activities) > 0:
        return True

    return False


def get_user_intervention_state(user_id: int) -> List[UserInterventionState]:
    """
       Get the user intervention state
        Args:
                user_id: the user_id of the user to retrieve the data for

            Returns:
                    The intervention state

    """
    session = get_db_session(db_url=DATABASE_URL)

    intervention_state = (
        session.query(
            UserInterventionState
        )
        .filter(
            UserInterventionState.users_nicedayuid == user_id
        )
        .all()
    )

    return intervention_state


def get_user_intervention_state_hrs(user_id: int) -> List[UserInterventionState]:
    """
       Get the user intervention state for the hrs dialogs
        Args:
                user_id: the user_id of the user to retrieve the data for

            Returns:
                    The intervention state for the hrs dialogs

    """
    session = get_db_session(db_url=DATABASE_URL)

    hrs_components = [Components.RELAPSE_DIALOG_HRS, Components.RELAPSE_DIALOG_RELAPSE,
                      Components.RELAPSE_DIALOG_LAPSE]

    intervention_state = (
        session.query(
            UserInterventionState
        )
        .join(InterventionComponents)
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            InterventionComponents.intervention_component_name in hrs_components
        )
        .all()
    )

    return intervention_state


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


def make_step_overview(date_array: List[str], step_array: List[int], step_goal: int) -> Any:
    """
       Makes the step overview for the weekly reflection dialog.
        Args:
                date_array: the list of dates for the y_axis
                step_array: the list of steps for the x_axis
                step_goal: the step goal of the user
            Returns:
                    A plot, showing the number of steps the user took each day
                    for a week, with a line representing the step goal and the
                    bars being green if they accomplished their goal and red if
                    not.
    """
    data = pd.DataFrame(
        {'date': date_array,
         'steps': step_array})

    data['goal_achieved'] = data['steps'] >= step_goal

    fig = go.Figure(go.Bar(x=data['steps'],
                           y=data['date'],
                           orientation='h',
                           marker=dict(color=data['goal_achieved'].map(
                               {True: 'green', False: 'red'}))))

    fig.add_shape(type='line',
                  x0=step_goal,
                  y0=-0.5,
                  x1=step_goal,
                  y1=len(data) - 0.5,
                  line=dict(color='black', width=3, dash='longdash'))

    fig.add_annotation(x=step_goal,
                       y=-1,
                       text=f'Step Goal: {step_goal}',
                       showarrow=False,
                       font=dict(size=14, color='black'))

    for i, step in enumerate(data['steps']):
        fig.add_annotation(x=step,
                           y=i,
                           text=str(step),
                           showarrow=False,
                           font=dict(size=12, color='black'),
                           xshift=5)

    fig.update_layout(title='Step overview',
                      height=500,
                      margin=dict(l=150),
                      xaxis=dict(tickformat='d'))
    return fig


def get_faik_text(user_id):
    session = get_db_session(db_url=DATABASE_URL)

    kit_text = ""
    filled = False  # Whether the first aid kit has content
    activity_ids_list = []  # List of activity IDs

    # get the highest scored activities
    top_five_activities = (
        session.query(
            FirstAidKit
        ).order_by(FirstAidKit.activity_rating.desc())
        .filter(
            FirstAidKit.users_nicedayuid == user_id
        )
        .limit(NUM_TOP_ACTIVITIES).all()
    )

    if top_five_activities is not None:
        for activity_idx, activity in enumerate(top_five_activities):
            kit_text += str(activity_idx + 1) + ") "
            kit_text += activity.intervention_activity.intervention_activity_title
            kit_text += ": " + activity.intervention_activity.intervention_activity_description
            if not activity_idx == len(top_five_activities) - 1:
                kit_text += "\n"

            activity_ids_list.append(activity.intervention_activity.intervention_activity_id)
        filled = True

    return kit_text, filled, activity_ids_list
