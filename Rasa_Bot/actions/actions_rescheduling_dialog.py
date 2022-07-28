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

celery = Celery(broker=REDIS_URL)


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

        now_or_later = self._validate_now_or_later_response(value)
        if now_or_later is None:
            dispatcher.utter_message(response="utter_please_answer_now_or_later")

        return {"rescheduling_now": now_or_later}

    @staticmethod
    def _validate_now_or_later_response(value):
        if value.lower() in ['nu', 'nou', 'nu is goed']:
            return True
        if value.lower() in ['later', 'later.', 'niet nu']:
            return False
        return None


class ActionGetReschedulingOptionsList(Action):
    """Get the possible rescheduling options."""

    def name(self):
        return "action_get_rescheduling_options_list"

    async def run(self, dispatcher, tracker, domain):

        options = get_reschedule_options_str()

        # Create string of options to utter them
        num_options = len(options)
        rescheduling_options_string = ""
        for o in range(num_options):
            rescheduling_options_string += "(" + str(o + 1) + ") " + options[o] + "."
            if not o == len(options) - 1:
                rescheduling_options_string += " "

        timestamp = datetime.datetime.timestamp(datetime.datetime.now())

        return [SlotSet("rescheduling_options_string", rescheduling_options_string),
                SlotSet("rescheduling_options_timestamp", timestamp)]


class ActionResetReschedulingOptionSlot(Action):
    """Reset rescheduling_option slot"""

    def name(self):
        return "action_reset_rescheduling_option_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("rescheduling_option", None)]


class ValidateReschedulingOptionsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_rescheduling_options_form'

    def validate_rescheduling_option(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate rescheduling_option input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"rescheduling_option": None}

        return {"rescheduling_option": int(value)}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 4):
            return False
        return True


class ActionRescheduleDialog(Action):
    """Reschedule the dialog at the chosen time"""

    def name(self):
        return "action_reschedule_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        chosen_option = tracker.get_slot('rescheduling_option')
        timestamp = tracker.get_slot('rescheduling_options_timestamp')
        dialog = tracker.get_slot('current_intervention_component')
        eta = get_reschedule_date(timestamp, chosen_option)

        celery.send_task('celery_tasks.reschedule_dialog', (user_id, dialog, eta))


def get_reschedule_options_str() -> list:

    options = ["In een uur"]

    current_time = datetime.datetime.now().astimezone(TIMEZONE)

    # In the morning
    if MORNING[0] <= current_time.hour < MORNING[1]:
        options += ["Vanmiddag, om 16:00",
                    "Vanavond, om 21:00",
                    "Morgenochtend om deze tijd"]

    # In the afternoon
    elif AFTERNOON[0] <= current_time.hour < AFTERNOON[1]:
        options += ["Vanavond, om 21:00",
                    "Morgenochtend, om 8:00",
                    "Morgenmiddag om deze tijd"]

    # In the evening
    elif EVENING[0] <= current_time.hour < EVENING[1]:
        options += ["Morgenochtend, om 8:00",
                    "Morgenmiddag, om 16:00",
                    "Morgenavond om deze tijd"]

    # In the night
    else:
        options += ["Om 16:00",
                    "Om 21:00",
                    "Morgen om deze tijd"]

    return options


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
