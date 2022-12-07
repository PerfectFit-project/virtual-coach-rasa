"""Unit tests for the custom actions"""
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from contextlib import contextmanager
from typing import Text, Union
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.interfaces import Tracker
from Rasa_Bot.actions.actions_general_activity import (
    CheckIfFirstExecutionGA,
    GetActivityUserInput,
    CheckUserInputRequired,
    CheckActivityDone,
    SaveDescriptionInDb,
    SetSlotGeneralActivity,
)

from Rasa_Bot.actions.actions_future_self_dialog import (
    ValidateWhyPickedMoverWordsForm,
)
from Rasa_Bot.actions.actions_minimum_functional_product import SavePlanWeekCalendar

from Rasa_Bot.tests.conftest import EMPTY_TRACKER
from virtual_coach_db.dbschema.models import (
    InterventionActivitiesPerformed,
    InterventionActivity,
)
from sqlalchemy import update
from virtual_coach_db.helper import ExecutionInterventionComponents


@pytest.fixture
def tracker() -> Tracker:
    yield EMPTY_TRACKER


@pytest.fixture
def mocker_db_session(mocker) -> MagicMock:
    mocker_get_db_session = mocker.patch("Rasa_Bot.actions.actions_general_activity.get_db_session")
    mocker_db_session = mocker.MagicMock(
        **{
            "query": mocker.MagicMock(
                return_value=mocker.MagicMock(**{"filter": mocker.MagicMock(return_value=mocker.MagicMock())})
            ),
            "execute": mocker.MagicMock(),
            "commit": mocker.MagicMock(),
        }
    )
    mocker_get_db_session.return_value = mocker_db_session
    yield mocker_db_session


@pytest.mark.asyncio
async def test_run_action_check_if_first_execution_ga__first_time(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckIfFirstExecutionGA()

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(return_value=[])
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )

    expected_events = [SlotSet("general_activity_first_execution", True)]
    assert expected_events == events


@pytest.mark.asyncio
async def test_run_action_check_if_first_execution_ga__not_first_time(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckIfFirstExecutionGA()

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[InterventionActivitiesPerformed()]
    )
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )

    assert events == [SlotSet("general_activity_first_execution", False)]


@pytest.mark.asyncio
async def test_run_action_get_activity_user_input(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11
    tracker.add_slots([SlotSet("last_activity_id_slot", last_activity_id_slot)])
    action = GetActivityUserInput()
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivitiesPerformed(user_input="user_input1"),
            InterventionActivitiesPerformed(user_input="user_input2"),
        ]
    )
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot
    )

    assert events == [SlotSet("activity_user_input", "user_input2")]


@pytest.mark.asyncio
async def test_run_action_check_user_input_required__required(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11
    tracker.add_slots([SlotSet("last_activity_id_slot", last_activity_id_slot)])
    action = CheckUserInputRequired()
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivity(user_input_required=False),
            InterventionActivity(user_input_required=True),
        ]
    )
    events = await action.run(dispatcher, tracker, domain)
    mocker_db_session.query.assert_called_once_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id == last_activity_id_slot
    )

    assert events == [SlotSet("is_user_input_required", False)]


@pytest.mark.asyncio
async def test_run_action_check_user_input_required__not_required(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11
    tracker.add_slots([SlotSet("last_activity_id_slot", last_activity_id_slot)])
    action = CheckUserInputRequired()
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivity(user_input_required=True),
            InterventionActivity(user_input_required=True),
        ]
    )
    events = await action.run(dispatcher, tracker, domain)
    mocker_db_session.query.assert_called_once_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id == last_activity_id_slot
    )

    assert events == [SlotSet("is_user_input_required", True)]


@pytest.mark.asyncio
async def test_run_action_check_activity_done__not_done(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11
    tracker.add_slots([SlotSet("last_activity_id_slot", last_activity_id_slot)])
    action = CheckActivityDone()
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivitiesPerformed(user_input="user_input1"),
            InterventionActivitiesPerformed(user_input=None),
        ]
    )
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot
    )

    assert events == [SlotSet("is_activity_done", False)]


@pytest.mark.asyncio
async def test_run_action_check_activity_done__done(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11
    tracker.add_slots([SlotSet("last_activity_id_slot", last_activity_id_slot)])
    action = CheckActivityDone()
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivitiesPerformed(user_input="user_input1"),
            InterventionActivitiesPerformed(user_input="user_input2"),
        ]
    )
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot
    )

    assert events == [SlotSet("is_activity_done", True)]


@pytest.mark.asyncio
async def test_run_action_save_description_in_db(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    description = "This is a description"
    last_activity_id_slot = 11
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
            SlotSet("general_activity_description_slot", description),
        ]
    )
    action = SaveDescriptionInDb()

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivitiesPerformed(intervention_activities_performed_id=1),
            InterventionActivitiesPerformed(intervention_activities_performed_id=2),
        ]
    )

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"]
    )
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot
    )
    statement = (
        update(InterventionActivitiesPerformed)
        .where(InterventionActivitiesPerformed.intervention_activities_performed_id == 2)
        .values(user_input=description)
    )
    mocker_db_session.execute.assert_called_once()
    mocker_db_session.execute.call_args.args[0].compare(statement)
    mocker_db_session.commit.assert_called_once()
    assert events == []


@pytest.mark.asyncio
async def test_run_action_set_slot_general_activity(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = SetSlotGeneralActivity()

    events = await action.run(dispatcher, tracker, domain)
    assert events == [SlotSet("current_intervention_component", ExecutionInterventionComponents.GENERAL_ACTIVITY)]


# TODO: If this is a recurring pattern, this can be turned into a fixture
@contextmanager
def latest_message(tracker, message):
    # this is not thread safe
    original = tracker.latest_message["text"]
    tracker.latest_message["text"] = message
    yield tracker
    tracker.latest_message["text"] = original


has_enough_words_examples = (
    ("too few", None),
    (
        "User provided enough words to analyze their response.",
        "User provided enough words to analyze their response.",
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response,expected",
    has_enough_words_examples,
    ids=("negative", "positive"),
)
async def test_run_action_validate_why_picked_mover_words_form(
    dispatcher: CollectingDispatcher,
    domain: DomainDict,
    response: Text,
    expected: Union[Text, None],
):
    with latest_message(EMPTY_TRACKER, response) as tracker:
        action = ValidateWhyPickedMoverWordsForm()
        slots = action.validate_why_picked_words(
            response,
            dispatcher,
            tracker,
            domain,
        )
        expected_slots = {"why_picked_words": expected}

        assert slots == expected_slots
