from typing import Optional

from celery import Celery
from datetime import datetime, date, timedelta
from sqlalchemy.exc import NoResultFound
from state_machine.const import (REDIS_URL, TIMEZONE, TRIGGER_COMPONENT,
                                 SCHEDULE_TRIGGER_COMPONENT, TRIGGER_INTENT)
from virtual_coach_db.dbschema.models import (ClosedAnswers, DialogClosedAnswers, DialogQuestions,
                                              InterventionComponents, InterventionPhases, Users,
                                              UserStateMachine, UserInterventionState)
from virtual_coach_db.helper.definitions import Components, ComponentsTriggers, DialogQuestionsEnum
from virtual_coach_db.helper.helper_functions import get_db_session

celery = Celery(broker=REDIS_URL)


def compute_next_day(selectable_days: list, current_date: datetime) -> date:
    """
    Given a list of days in the week, returns the date of
    the closest future day among the ones provided in the list

    Args:
        selectable_days: a list of the week days among to search for.
                         The list is a list of int, each int represents
                         the day of the week (e.g., 1 = Monday
        current_date: the date to start from

    Returns:
        The date of the next day available in the list, starting from
             current date.
    """
    # get the weekday number of current date
    today = current_date
    today_weekday = today.isoweekday()

    selectable_days.sort()
    # get the nex usable day in the week
    available_days = [i for i in selectable_days if i > today_weekday]

    if available_days:
        # if there are available day further in the week, get the next one
        next_weekday = available_days[0]
    else:
        # if no further days are available, get the first available in the week
        next_weekday = selectable_days[0]

    # compute the date of the next selected day
    next_date = today + timedelta((next_weekday - today_weekday) % 7)

    return next_date


def create_new_date(start_date: date,
                    time_delta: int = 0,
                    hour: int = 10,
                    minute: int = 00) -> datetime:
    """
    Create a new timedate object from the date object. It adds a 'time_delta'
    number of days to the starting date

    Args:
        start_date: the date to start from
        time_delta: the number of days to be added to the start_date
        hour: the hour to be used in the new date
        minute: the minute to be used in the new date

    Returns:
        A datetime object with the start_date + time_delta number of days and the
        hour specified

    """
    new_date = start_date + timedelta(days=time_delta)
    new_timedate = datetime(new_date.year, new_date.month, new_date.day, hour, minute,
                            tzinfo=TIMEZONE)

    return new_timedate


def get_all_scheduled_occurrence(user_id: int,
                                 intervention_component_id: int,
                                 current_date: datetime) -> Optional[UserInterventionState]:
    """
    Gets the all the intervention component occurrences planned for the future and not completed

    Args:
        user_id: the id of the user
        intervention_component_id: the id of the intervention component as
            saved in the DB
        current_date: the date after which look for the planned component

    Returns:
            All the occurrence planned for the future and saved in the user_intervention_state
            table in the DB for the given user and intervention component.
            A list of UserInterventionState object is returned.
            In case no entry is found, it returns None
    """
    session = get_db_session()

    try:
        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                UserInterventionState.intervention_component_id == intervention_component_id,
                UserInterventionState.next_planned_date > current_date
            )
            .order_by(UserInterventionState.next_planned_date.asc())  # order by ascending date
            .all()
        )
    except NoResultFound:
        result = None
    else:
        result = [UserInterventionState(id=task.id,
                                        users_nicedayuid=task.users_nicedayuid,
                                        intervention_phase_id=task.intervention_phase_id,
                                        intervention_component_id=task.intervention_component_id,
                                        completed=task.completed,
                                        last_time=task.last_time,
                                        last_part=task.last_part,
                                        next_planned_date=task.next_planned_date,
                                        task_uuid=task.task_uuid) for task in selected]
    session.close()

    return result


def get_dialog_completion_state(user_id: int, dialog_name: str) -> Optional[bool]:
    """
    Get the completion state of the last dialog occurrence in the DB
    Args:
        user_id: the id of the user
        dialog_name: name of the dialog

    Returns: True if the dialog has been completed, False otherwise

    """

    component = get_intervention_component(dialog_name)

    session = get_db_session()

    selected = (
        session.query(
            UserInterventionState
        )
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            UserInterventionState.intervention_component_id == component.intervention_component_id
        )
        .order_by(UserInterventionState.last_time.desc())  # order by descending date
        .limit(1)  # get only the first result
        .one_or_none()
    )

    if selected is not None:
        completed = selected.completed
        session.close()
        return completed

    session.close()
    return None


def get_last_component_state(user_id: int, intervention_component_id: int) -> UserInterventionState:
    """
    Gets the last state saved in the DB for an intervention component

    Args:
        intervention_component_id:id of the dialog
        user_id: the id of the user
        intervention_component_id: the id of the intervention component as
            saved in the DB

    Returns:
            The last row saved in the user_intervention_state table in the DB for the
            given user and intervention component. A UserInterventionState object is
            returned. In case no entry is found, it returns None
    """
    session = get_db_session()

    selected = (
        session.query(
            UserInterventionState
        )
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            UserInterventionState.intervention_component_id == intervention_component_id
        )
        .order_by(UserInterventionState.id.desc())  # order by descending id
        .limit(1)  # get only the first result
        .one_or_none()
    )
    if selected is not None:
        session.expunge(selected)

    session.close()

    return selected


def get_last_scheduled_occurrence(user_id: int,
                                  intervention_component_id: int) -> UserInterventionState:
    """
    Gets the last planned intervention component occurrence

    Args:
        user_id: the id of the user
        intervention_component_id: the id of the intervention component as
            saved in the DB

    Returns:
            The next last occurrence saved in the user_intervention_state table in the DB for the
            given user and intervention component. A UserInterventionState object is
            returned. In case no entry is found, it returns None
    """
    session = get_db_session()

    try:
        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                UserInterventionState.intervention_component_id == intervention_component_id
            )
            .order_by(UserInterventionState.next_planned_date.desc())  # order by descending date
            .limit(1)  # get only the first result
            .one()
        )
    except NoResultFound:
        selected = None

    session.expunge(selected)
    session.close()

    return selected


def get_next_scheduled_occurrence(user_id: int,
                                  intervention_component_id: int,
                                  current_date: datetime) -> Optional[UserInterventionState]:
    """
    Gets the next planned intervention component occurrence

    Args:
        user_id: the id of the user
        intervention_component_id: the id of the intervention component as
            saved in the DB
        current_date: the date after which look for the planned component

    Returns:
            The next planned occurrence saved in the user_intervention_state table in the DB for the
            given user and intervention component. A UserInterventionState object is
            returned. In case no entry is found, it returns None
    """
    session = get_db_session()

    try:
        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                UserInterventionState.intervention_component_id == intervention_component_id,
                UserInterventionState.next_planned_date > current_date
            )
            .order_by(UserInterventionState.next_planned_date.asc())  # order by ascending date
            .limit(1)  # get only the first result
            .one()
        )
    except NoResultFound:
        session.close()
        return None

    session.expunge(selected)
    session.close()

    return selected


def get_current_phase(user_id: int) -> InterventionPhases:
    """
    Get the current phase of the intervention of a user.

    Args:
        user_id: the id of the user

    Returns:
            The current intervention phase for the given user as
            an InterventionPhases object.

    """
    session = get_db_session()

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

    session.expunge(phase)
    session.close()

    return phase


def get_intervention_component(intervention_component_name: str) -> InterventionComponents:
    """
    Get the intervention component as stored in the DB from the
    intervention component's name.

    Args:
        intervention_component_name: the name of the intervention component.
                                The names are listed in virtual_coach_db.helper.definitions
                                in the Components class

    Returns:
            The intervention component as an InterventionComponents object.

    """
    session = get_db_session()

    selected = (
        session.query(
            InterventionComponents
        )
        .filter(
            InterventionComponents.intervention_component_name == intervention_component_name
        )
        .one_or_none()
    )
    session.expunge(selected)
    session.close()

    return selected


def get_hrs_last_branch(user_id: int) -> Optional[Components]:
    """
    Check which is the currently run branch of the hrs dialog. If the answer is not recent
    (stored before the last execution of the hrs dialog), a None value is returned
    Args:
        user_id: id of the user

    Returns: The most recent compoinent of the hrs dialog component, if a recent one is present.
    None otherwise

    """
    session = get_db_session()

    last_execution = (
        session.query(
            UserInterventionState
        )
        .join(InterventionComponents)
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            InterventionComponents.intervention_component_name == Components.RELAPSE_DIALOG.value
        )
        .order_by(
            UserInterventionState.last_time.desc()
        )
        .limit(1)
        .one_or_none()
    )

    if last_execution is None:
        session.close()
        return None

    last_answer = (
        session.query(
            DialogClosedAnswers
        )
        .join(ClosedAnswers, DialogQuestions)
        .filter(
            DialogQuestions.question_id == DialogQuestionsEnum.RELAPSE_SMOKE_HRS_LAPSE_RELAPSE.value
        )
        .order_by(DialogClosedAnswers.datetime.desc())
        .limit(1)
        .one_or_none()
    )

    # if there are no answers or the answer came before the last execution of the dialog,
    # return None
    if last_answer is None or last_answer.datetime < last_execution.last_time:
        return None

    # when we populate the DB, the answer id is set by adding the answer value
    # to 100 times the question ID. Here we do the inverse computation
    answer_id = last_answer.closed_answers_id
    question_id = last_answer.closed_answers.dialog_questions.question_id

    answer = answer_id - (question_id * 100)

    if answer == 1:
        component = Components.RELAPSE_DIALOG_HRS
    elif answer == 2:
        component = Components.RELAPSE_DIALOG_LAPSE
    elif answer == 3:
        component = Components.RELAPSE_DIALOG_RELAPSE
    else:
        component = None

    session.close()

    return component


def get_next_planned_date(user_id: int,
                          current_date: datetime) -> datetime:
    """
    Get the date planned for the administration of an intervention component, considering
    the user preferences saved in the DB.

    Args:
        user_id: the id of the user
        current_date: the current date

    Returns:
            The date planned for the execution of the component.

    """

    date_time = get_preferred_date_time(user_id=user_id)

    # first element of the tuple is the list of days
    pref_days = date_time[0]
    # second element of the tuple is the time
    pref_time = date_time[1]

    next_day = compute_next_day(pref_days, current_date)

    next_planned_date = datetime.combine(next_day, pref_time)

    return next_planned_date


def get_pa_group(user_id: int) -> int:
    """
        Get the physical activity group of a user.

        Args:
            user_id: the id of the user

        Returns:
                The PA group (1 or 2)
        """
    session = get_db_session()

    user = (session.query(Users).filter(Users.nicedayuid == user_id).first())

    session.expunge(user)
    session.close()

    return user.pa_intervention_group


def get_phase_object(phase_name: str) -> InterventionPhases:
    """
    Get the phase as stored in the DB from the phase name.

    Args:
        phase_name: the name of the intervention component.
                    The names are listed in virtual_coach_db.helper.definitions
                    in the Phases class

    Returns:
            The phase as an InterventionPhases object.

    """
    session = get_db_session()

    phases = (
        session.query(
            InterventionPhases
        )
        .filter(
            InterventionPhases.phase_name == phase_name
        )
        .one_or_none()
    )

    session.expunge(phases)
    session.close()

    return phases


def get_preferred_date_time(user_id: int) -> tuple:
    """
    Gets the preferred day of the week and the preferred time of the day
    set by the user
    Args:
        user_id: ID of the user
        intervention_component_id: the id of the interventions component

    Returns: the list of preferred days and time

    """
    session = get_db_session()
    users = (
        session.query(
            Users
        )
        .filter(
            Users.nicedayuid == user_id
        )
        .one()
    )

    try:
        days_str = users.week_days
        days_list = list(map(int, days_str.split(',')))
    except Exception:
        days_list = None

    if (user_time := users.preferred_time) is not None:
        preferred_time = user_time.time()
    else:
        preferred_time = None

    session.close()

    return days_list, preferred_time


def store_intervention_component_to_db(state: UserInterventionState):
    """
    Writes a new row in the user_intervention_state table in the DB.

    Args:
        state: the UserInterventionState to be written int the DB

    """

    session = get_db_session()  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=state.users_nicedayuid).one()

    entry = UserInterventionState(
        intervention_phase_id=state.intervention_phase_id,
        intervention_component_id=state.intervention_component_id,
        completed=state.completed,
        last_time=state.last_time,
        last_part=state.last_part,
        next_planned_date=state.next_planned_date,
        task_uuid=state.task_uuid
    )

    selected.user_intervention_state.append(entry)

    session.commit()  # Update database

    session.close()


def get_start_date(user_id: int) -> date:
    """
    Retrieve teh starting date of the intervention for a user
    Args:
        user_id: ID of the user

    Returns: the intervention starting date

    """
    session = get_db_session()

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    start_date = selected.start_date

    session.close()

    return start_date


def get_quit_date(user_id: int) -> date:
    """
    Retrieve the smoking quit date of a user
    Args:
        user_id: ID of the user

    Returns: the smoking quit starting date

    """
    session = get_db_session()

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    quit_date = selected.quit_date

    session.close()

    return quit_date


def get_execution_week(user_id: int) -> int:
    """
    Computes the current wek number of the execution phase
    Args:
        user_id: ID of the user

    Returns: the week number

    """

    session = get_db_session()

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())
    week_number = int(selected.execution_week)

    session.close()

    return week_number


def compute_spent_weeks(current_date: date, starting_date: date) -> int:
    """
    Compute the number of weeks between two dates
    Args:
        current_date: the current date
        starting_date: the date from which to start the weeks counting

    Returns: The number of weeks beetween the two dates

    """
    spent_days = (current_date - starting_date).days

    spent_weeks = spent_days // 7

    return spent_weeks


def is_new_week(current_date: date, starting_date: date) -> bool:
    """

    Args:
        current_date: the current date
        starting_date: the date which to check against with if a new
        week has started

    Returns: True if the current_date is exctly at the beginning of a
    new week, false otherwise

    """
    spent_days = (current_date - starting_date).days

    if spent_days > 0 and spent_days % 7 == 0:
        return True

    return False


def update_execution_week(user_id: int, week_number: int):
    """
    Computes the current wek number of the execution phase
    Args:
        user_id: ID of the user
        week_number: execution week number

    Returns: the week number

    """
    session = get_db_session()

    selected = (session.query(Users)
                .filter(Users.nicedayuid == user_id)
                .one())

    selected.execution_week = week_number

    session.commit()

    session.close()


def update_fsm_dialog_running_status(user_id: int, dialog_running: bool):
    """
    Computes the current wek number of the execution phase
    Args:
        user_id: ID of the user
        dialog_running: value to be set in the dialog_running field of the fsm

    """
    session = get_db_session()

    selected = (session.query(UserStateMachine)
                .filter(UserStateMachine.users_nicedayuid == user_id)
                .one())

    selected.dialog_running = dialog_running

    session.commit()

    session.close()


def dialog_to_be_completed(user_id: int) -> Optional[UserInterventionState]:
    """
    Checks if a dialog has to be completed and, in this case returns it. If no dialogs have to be
    completed, it triggers the menu message without the option of resuming a dialog

    Args:
        user_id: ID of the user
    Returns:
        The component to be completed

    """

    session = get_db_session()

    uncompleted = (
        session.query(
            UserInterventionState
        ).order_by(UserInterventionState.last_time.desc())
        .filter(
            UserInterventionState.users_nicedayuid == user_id,
            UserInterventionState.completed.is_(False),
            UserInterventionState.last_time.isnot(None)
        )
        .first()
    )

    session.expunge(uncompleted)

    session.close()

    if uncompleted is not None:
        return uncompleted

    return None


def run_uncompleted_dialog(user_id: int):
    """
    Checks if a dialog has to be completed and, in this case runs it from the latest completed part.

    Args:
        user_id: ID of the user

    """

    uncompleted = dialog_to_be_completed(user_id)

    if uncompleted is not None:
        # update the time in the DB and trigger it
        session = get_db_session()

        component = (session.query(UserInterventionState)
                     .filter(UserInterventionState.id == uncompleted.id)
                     .first())

        component.last_time = datetime.now().astimezone(TIMEZONE)
        session.commit()

        celery.send_task(
            TRIGGER_COMPONENT,
            (user_id, component.intervention_component.intervention_component_trigger)
        )
        session.close()
    else:
        run_option_menu(user_id)


def run_option_menu(user_id: int):
    """
    Runs a celery task for showing the options' menu.

    Args:
        user_id: ID of the user

    """

    celery.send_task(TRIGGER_INTENT, (user_id, ComponentsTriggers.CENTRAL_OPTIONS, False))


def retrieve_tracking_day(user_id: int, current_date: date) -> int:
    """
    Computes the number of days from the start day of the tracking
    (completion of the track smoking behavior dialog)

    Args:
        user_id: ID of the user
        current_date: the current date

    Returns:
        The number of days since the tracking start day

    """
    track_dialog_id = get_intervention_component(Components.PROFILE_CREATION)
    track_dialog = get_last_component_state(user_id, track_dialog_id.intervention_component_id)

    # if the dialog has not been administered or not completed, return 0
    if track_dialog is None:
        tracking_day = 0
    elif not track_dialog.completed:
        tracking_day = 0
    else:
        start_date = track_dialog.last_time

        # add +1 because the count starts at day 1
        tracking_day = (current_date - start_date).days + 1

    return tracking_day


def save_fsm_state_in_db(user_id: int, state: str):
    """
    Save the state in the fsm in the db
    Args:
        user_id: id of the user
        state: state to be saved

    """
    session = get_db_session()

    user_fsm = (session.query(UserStateMachine)
                .filter(UserStateMachine.users_nicedayuid == user_id)
                .first())

    # if a machine already exists, use the same primary key to update the row
    if user_fsm is not None:
        user_fsm.state = state

        session.merge(user_fsm)
        session.commit()

    session.close()


def store_rescheduled_dialog(user_id: int,
                             dialog_id: int,
                             phase_id: int,
                             planned_date: datetime,
                             task_uuid: Optional[str] = None):
    """
    This function marks when a dialog has been rescheduled, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog_id: db id of the dialog
        phase_id: id of the intervention phase
        planned_date: date when the dialog is to be delivered
        task_uuid: celery task uuid

    """
    # get the id of the dialog
    last_state = get_last_component_state(user_id=user_id,
                                          intervention_component_id=dialog_id)

    # update the dialog entry, setting a new date an uuid
    if last_state is not None:
        last_state.last_time = datetime.now().astimezone(TIMEZONE)
        session = get_db_session()
        selected = (session.query(UserInterventionState)
                    .filter(UserInterventionState.id == last_state.id)
                    .one())

        selected.next_planned_date = planned_date
        selected.task_uuid = task_uuid

        session.commit()

        session.close()


    # if for any reason the dialog starting was not recorded in the DB, create the entry
    else:
        state = UserInterventionState(
            users_nicedayuid=user_id,
            intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
            intervention_component_id=dialog_id,
            completed=False,
            last_time=datetime.now().astimezone(TIMEZONE),
            last_part=0,
            next_planned_date=planned_date,
            task_uuid=task_uuid
        )
        # record the dialog completion in the DB
        store_intervention_component_to_db(state)


def store_completed_dialog(user_id: int, dialog: str, phase_id: int):
    """
    This function marks when a dialog has been completed, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog: name of the dialog
        phase_id: id of the intervention phase

    """
    # get the id of the dialog
    dialog = get_intervention_component(dialog)
    last_state = get_last_component_state(user_id,
                                          dialog.intervention_component_id)

    # update the dialog entry, setting the `completed` filed to true
    if last_state is not None:
        last_state.last_time = datetime.now().astimezone(TIMEZONE)
        session = get_db_session()
        selected = (session.query(UserInterventionState)
                    .filter(UserInterventionState.id == last_state.id)
                    .one())

        uuid = selected.task_uuid
        selected.completed = True

        session.commit()

        session.close()

        # if the user completes a dialog which was scheduled, we don't
        # want that to be re-proposed
        if uuid is not None:
            celery.control.revoke(uuid)

    # if for any reason the dialog starting was not recorded in the DB, create the entry
    else:
        state = UserInterventionState(
            users_nicedayuid=user_id,
            intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
            intervention_component_id=dialog.intervention_component_id,
            completed=True,
            last_time=datetime.now().astimezone(TIMEZONE),
            last_part=0,
            next_planned_date=None,
            task_uuid=None
        )
        # record the dialog completion in the DB
        store_intervention_component_to_db(state)


def store_scheduled_dialog(user_id: int,  # pylint: disable=too-many-arguments
                           dialog_id: int,
                           phase_id: int,
                           planned_date: datetime = datetime.now().astimezone(TIMEZONE),
                           task_uuid: Optional[str] = None,
                           last_time: Optional[datetime] = None):
    """
    This function marks when a dialog has been completed, by update or creating
    the entry in the DB
    Args:
        user_id: id of the user
        dialog_id: db id of the dialog
        phase_id: id of the intervention phase
        planned_date: date when the dialog is to be delivered
        task_uuid: celery task uuid
        last_time: date of the last time the dialog was presented to the user

    """
    # get the id of the dialog

    state = UserInterventionState(
        users_nicedayuid=user_id,
        intervention_phase_id=phase_id,  # probably we don't need this any longer in the DB
        intervention_component_id=dialog_id,
        completed=False,
        last_time=last_time,
        last_part=0,
        next_planned_date=planned_date,
        task_uuid=task_uuid
    )
    # record the dialog completion in the DB
    store_intervention_component_to_db(state)


def plan_and_store(user_id: int,
                   dialog: str,
                   phase_id: int,
                   planned_date: Optional[datetime] = None,
                   last_time: Optional[datetime] = None):
    """
    Program a celery task for the planned_date, or sends it immediately in case
    planned_date is None, and stores the new component to the DB
    Args:
        user_id:user id
        dialog: dialog to be triggered
        phase_id: db id of the phase
        planned_date: date when the dialog has to be triggered
    Returns:

    """

    component = get_intervention_component(dialog)
    dialog_id = component.intervention_component_id
    trigger = component.intervention_component_trigger

    if planned_date is None:
        celery.send_task(TRIGGER_COMPONENT, (user_id, trigger))

        store_scheduled_dialog(user_id=user_id,
                               dialog_id=dialog_id,
                               phase_id=phase_id,
                               last_time=datetime.now().astimezone(TIMEZONE))
    else:
        task = celery.send_task(SCHEDULE_TRIGGER_COMPONENT,
                                (user_id, trigger),
                                eta=planned_date)

        store_scheduled_dialog(user_id=user_id,
                               dialog_id=dialog_id,
                               phase_id=phase_id,
                               planned_date=planned_date,
                               task_uuid=str(task.task_id),
                               last_time=last_time)


def plan_every_day_range(user_id: int,
                         dialog: str,
                         phase_id: int,
                         first_date: date,
                         last_date: date):
    """
    Program a dialog every day from the first date to the last date.
    Args:
        user_id:user id
        dialog: dialog to be triggered
        phase_id: db id of the phase
        first_date: first date where the dialog is planned
        last_date: last date where the dialog is planned
    """

    for day in range((last_date - first_date).days + 1):
        planned_date = create_new_date(start_date=first_date,
                                       time_delta=day)

        plan_and_store(user_id=user_id,
                       dialog=dialog,
                       planned_date=planned_date,
                       phase_id=phase_id)


def reschedule_dialog(user_id: int, dialog: str, planned_date: datetime, phase: int):
    """
    Program a new celery task for the planned_date and store the info in the db
    Args:
        user_id:user id
        dialog: dialog to be triggered
        planned_date: date when the dialog has to be triggered
        phase: db id of the phase
    Returns:

    """

    component = get_intervention_component(dialog)
    dialog_id = component.intervention_component_id
    trigger = component.intervention_component_trigger

    task = celery.send_task(SCHEDULE_TRIGGER_COMPONENT,
                            (user_id, trigger),
                            eta=planned_date)

    store_rescheduled_dialog(user_id=user_id,
                             dialog_id=dialog_id,
                             phase_id=phase,
                             planned_date=planned_date,
                             task_uuid=str(task.task_id))


def revoke_execution(task_uuid: str):
    """
    Revoke the execution of a planned task
    Args:
        task_uuid: the uuid of the celery task to be revoked

    """
    celery.control.revoke(task_uuid)


def schedule_next_execution(user_id: int, dialog: str, phase_id: int, current_date: datetime):
    """
    Get the next expected execution date for an intervention component,
    and schedules it
    Args:
        user_id: id of the user
        dialog: Name of the component
        phase_id: db id of the phase
        current_date: the current date

    """

    planned_date = get_next_planned_date(user_id=user_id,
                                         current_date=current_date)

    plan_and_store(user_id=user_id,
                   dialog=dialog,
                   planned_date=planned_date,
                   phase_id=phase_id)
