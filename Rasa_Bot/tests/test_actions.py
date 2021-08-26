"""Unit tests for the custom actions"""
import pytest

from tests.conftest import WEEKLY_PLAN_TRACKER

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet

from actions import actions


# NB: Update once the function tested here works correctly
@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar( 
    dispatcher: CollectingDispatcher, domain: DomainDict):
    tracker = WEEKLY_PLAN_TRACKER
    action = actions.SavePlanWeekCalendar()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events
    