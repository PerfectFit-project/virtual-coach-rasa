"""
Contains custom actions for rescheduling dialog
"""
from celery import Celery
import datetime
from typing import Any, Dict, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction

from .definitions import REDIS_URL
from .definitions import TIMEZONE
from .definitions import MORNING, AFTERNOON, EVENING
from .helper import get_latest_bot_utterance

from virtual_coach_db.helper import ComponentsTriggers

from . import validator


celery = Celery(broker=REDIS_URL)


class ActionContinueGeneralActivityDialog(Action):
    def name(self) -> Text:
        return "action_continue_with_general_activity"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, ComponentsTriggers.CONTINUE_GENERAL_ACTIVITY))


class ActionResetReschedulingNowSlot(Action):
    """Reset rescheduling_now slot"""

    def name(self):
        return "action_reset_rescheduling_now_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("rescheduling_now", None)]


class ValidateReschedulingNowOrLaterForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_rescheduling_now_or_later_form'

    def validate_rescheduling_now(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate rescheduling_now input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_rescheduling_now_or_later_form_rescheduling_now':
            return {"rescheduling_now": None}

        now_or_later = validator.validate_number_in_range_response(1, 2, value)
        if not now_or_later:
            dispatcher.utter_message(response="utter_please_answer_1_2")

        return {"rescheduling_now": value}

class ActionRescheduleDialog(Action):
    """Reschedule the dialog at the chosen time"""

    def name(self):
        return "action_reschedule_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        chosen_option = int(tracker.get_slot('chosen_daypart'))
        timestamp = tracker.get_slot('daypart_options_timestamp')
        dialog = tracker.get_slot('current_intervention_component')
        eta = get_reschedule_date(timestamp, chosen_option)

        celery.send_task('celery_tasks.reschedule_dialog', (user_id, dialog, eta))


def get_reschedule_date(timestamp: float, choice: int) -> datetime.datetime:

    dt_object = datetime.datetime.fromtimestamp(timestamp, TIMEZONE)

    morning_time = dt_object.replace(hour=8, minute=0, second=0)
    afternoon_time = dt_object.replace(hour=16, minute=0, second=0)
    evening_time = dt_object.replace(hour=21, minute=0, second=0)

    if choice == 1:
        reschedule_time = dt_object + datetime.timedelta(hours=1)
    elif choice == 4:
        reschedule_time = dt_object + datetime.timedelta(days=1)
    else:
        if MORNING[0] <= dt_object.hour < MORNING[1]:
            if choice == 2:
                reschedule_time = afternoon_time
            elif choice == 3:
                reschedule_time = evening_time

        # In the afternoon
        elif AFTERNOON[0] <= dt_object.hour < AFTERNOON[1]:
            if choice == 2:
                reschedule_time = evening_time
            elif choice == 3:
                reschedule_time = morning_time + datetime.timedelta(days=1)

        # In the evening
        elif EVENING[0] <= dt_object.hour < EVENING[1]:
            if choice == 2:
                reschedule_time = morning_time + datetime.timedelta(days=1)
            elif choice == 3:
                reschedule_time = afternoon_time + datetime.timedelta(days=1)

        # In the night
        else:
            if choice == 2:
                reschedule_time = afternoon_time
            elif choice == 3:
                reschedule_time = evening_time

    return reschedule_time


class ActionSetContinuation(Action):
    """Set the dialog_to_continue slot"""

    def name(self):
        return "action_set_continuation"

    async def run(self, dispatcher, tracker, domain):
        current_intervention = tracker.get_slot('current_intervention_component')

        return [SlotSet("dialog_to_continue", current_intervention)]
