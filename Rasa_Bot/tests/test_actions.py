"""Unit tests for the custom actions"""
import pytest

from rasa_sdk.events import SlotSet

from tests.conftest import WEEKLY_PLAN_TRACKER

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from actions import actions

# Update once the function tested here works correctly
def test_run_action_save_plan_week_calendar( 
    dispatcher: CollectingDispatcher,
    domain: DomainDict):
    tracker = WEEKLY_PLAN_TRACKER
    action = actions.SavePlanWeekCalendar()
    events = action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("success_save_calendar_plan_week", True),
    ]
    assert events == expected_events