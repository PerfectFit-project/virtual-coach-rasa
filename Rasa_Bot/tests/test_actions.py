"""Unit tests for the custom actions"""
import pytest
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from Rasa_Bot.tests.conftest import EMPTY_TRACKER

from Rasa_Bot.actions import actions


# NB: This is just an example test. The custom action tested here
# is currently just a placeholder function. Update once the
# function tested here works correctly.
@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar(
        dispatcher: CollectingDispatcher, domain: DomainDict):
    tracker = EMPTY_TRACKER
    action = actions.SavePlanWeekCalendar()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events
