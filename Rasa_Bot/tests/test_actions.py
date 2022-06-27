"""Unit tests for the custom actions"""
import pytest
from unittest import mock
from contextlib import contextmanager
from typing import Text, Union
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

from Rasa_Bot.actions.actions_future_self_dialog import ValidateWhyPickedMoverWordsForm
from Rasa_Bot.actions.actions_minimum_functional_product import (SavePlanWeekCalendar,
                                                                 ActionStorePaEvaluation)
from Rasa_Bot.tests.conftest import EMPTY_TRACKER


# NB: This is just an example test. The custom action tested here
# is currently just a placeholder function. Update once the
# function tested here works correctly.
@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar(
        dispatcher: CollectingDispatcher, domain: DomainDict):
    tracker = EMPTY_TRACKER
    action = SavePlanWeekCalendar()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events


@pytest.mark.asyncio
@mock.patch("Rasa_Bot.actions.actions_minimum_functional_product.get_db_session")
async def test_run_action_store_pa_evaluation(
        mock_get_db_session, dispatcher: CollectingDispatcher, domain: DomainDict):
    mock_result = mock.MagicMock(name="mock_result")
    mock_session = mock_get_db_session.return_value
    mock_session.query.return_value.filter_by.return_value \
        .one.return_value = mock_result
    tracker = EMPTY_TRACKER
    test_evaluation_response = 3
    tracker.slots['pa_evaluation_response'] = test_evaluation_response
    action = ActionStorePaEvaluation()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [SlotSet("pa_evaluation_response", None)]
    assert events == expected_events
    mock_session.commit.assert_called_once()


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
