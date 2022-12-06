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
from Rasa_Bot.actions.actions_general_activity import CheckIfFirstExecutionGA, GetActivityUserInput

from Rasa_Bot.actions.actions_future_self_dialog import (
    ValidateWhyPickedMoverWordsForm,
)
from Rasa_Bot.actions.actions_minimum_functional_product import SavePlanWeekCalendar

from Rasa_Bot.tests.conftest import EMPTY_TRACKER
from virtual_coach_db.dbschema.models import InterventionActivitiesPerformed
from sqlalchemy import and_

# NB: This is just an example test. The custom action tested here
# is currently just a placeholder function. Update once the
# function tested here works correctly.


@pytest.fixture
def tracker() -> Tracker:
    yield EMPTY_TRACKER


@pytest.fixture
def mocker_db_session(mocker) -> MagicMock:
    mocker_get_db_session = mocker.patch("Rasa_Bot.actions.actions_general_activity.get_db_session")
    mocker_db_session = mocker.MagicMock(
        query=mocker.MagicMock(return_value=mocker.MagicMock(filter=mocker.MagicMock(return_value=mocker.MagicMock())))
    )
    mocker_get_db_session.return_value = mocker_db_session
    yield mocker_db_session


@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar(dispatcher: CollectingDispatcher, domain: DomainDict):
    tracker = EMPTY_TRACKER
    action = SavePlanWeekCalendar()

    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events


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
async def test_get_activity_user_input(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    last_activity_id_slot = 11.0
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
    assert events == [SlotSet("activity_user_input", "user_input2")]


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
