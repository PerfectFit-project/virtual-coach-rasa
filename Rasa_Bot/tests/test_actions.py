"""Unit tests for the custom actions"""
import pytest
from pytest_mock import MockerFixture
from contextlib import contextmanager
from typing import Text, Union
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.interfaces import Tracker
from Rasa_Bot.actions.actions_general_activity import CheckIfFirstExecutionGA

from Rasa_Bot.actions.actions_future_self_dialog import (
    ValidateWhyPickedMoverWordsForm,
)
from Rasa_Bot.actions.actions_minimum_functional_product import SavePlanWeekCalendar

from Rasa_Bot.tests.conftest import EMPTY_TRACKER
from sqlalchemy.orm import Session
from virtual_coach_db.dbschema.models import InterventionActivitiesPerformed, FirstAidKit, InterventionActivity

# NB: This is just an example test. The custom action tested here
# is currently just a placeholder function. Update once the
# function tested here works correctly.


@pytest.fixture
def tracker() -> Tracker:
    yield EMPTY_TRACKER


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
    mocker: MockerFixture, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
) -> None:
    action = CheckIfFirstExecutionGA()
    mocker_get_db_session = mocker.patch("virtual_coach_db.helper.helper_functions.get_db_session")
    mocker_db_session = mocker.MagicMock()
    mocker_get_db_session.return_value = mocker_db_session
    mocker_filter = mocker.MagicMock()
    mocker_query = mocker.MagicMock(return_value=mocker_filter)
    mocker_db_session.query = mocker_query

    events = await action.run(dispatcher, tracker, domain)

    mocker_query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_filter.assert_called_once_with(InterventionActivitiesPerformed.users_nicedayuid == tracker.sender_id)
    mocker_filter.all = mocker.MagicMock(return_value=[InterventionActivitiesPerformed()])
    assert events == [SlotSet("general_activity_first_execution"), True]


@pytest.mark.asyncio
async def test_run_action_check_if_first_execution_ga__not_first_time(
    mocker: MockerFixture, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
) -> None:
    action = CheckIfFirstExecutionGA()
    mocker_get_db_session = mocker.patch("virtual_coach_db.helper.helper_functions.get_db_session")
    mocker_db_session = mocker.MagicMock()
    mocker_get_db_session.return_value = mocker_db_session
    mocker_filter = mocker.MagicMock()
    mocker_query = mocker.MagicMock(return_value=mocker_filter)
    mocker_db_session.query = mocker_query

    events = await action.run(dispatcher, tracker, domain)

    mocker_query.assert_called_once_with(InterventionActivitiesPerformed)
    mocker_filter.assert_called_once_with(InterventionActivitiesPerformed.users_nicedayuid == tracker.sender_id)
    mocker_filter.all = mocker.MagicMock(
        return_value=[InterventionActivitiesPerformed(), InterventionActivitiesPerformed()]
    )
    assert events == [SlotSet("general_activity_first_execution"), False]


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
