"""Unit tests for the custom actions"""
import pytest

from rasa_sdk.executor import CollectingDispatcher, Tracker
from rasa_sdk.events import SlotSet, ActionExecuted, SessionStarted

from tests.conftest import EMPTY_TRACKER, PAY_CC_CONFIRMED, PAY_CC_NOT_CONFIRMED
from actions import actions

@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar(dispatcher, domain):
    tracker = EMPTY_TRACKER
    action = actions.SavePlanWeekCalendar()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events