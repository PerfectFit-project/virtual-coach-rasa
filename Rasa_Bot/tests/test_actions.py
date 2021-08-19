"""Unit tests for the custom actions"""
import pytest

from rasa_sdk.events import SlotSet

import pathlib
print(pathlib.Path(__file__).parent.resolve())

print(pathlib.Path().resolve())

from conftest import WEEKLY_PLAN_TRACKER

from ..actions import actions

@pytest.mark.asyncio
async def test_run_action_save_plan_week_calendar(dispatcher, domain):
    tracker = WEEKLY_PLAN_TRACKER
    action = actions.SavePlanWeekCalendar()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events