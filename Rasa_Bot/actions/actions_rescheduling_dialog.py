"""
Contains custom actions for rescheduling dialog
"""
import datetime, timedelta
from typing import Any, Dict, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction

from .definitions import TIMEZONE


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

        # define morning, afternoon, evening
        MORNING = (6, 12)
        AFTERNOON = (12, 18)
        EVENING = (18, 24)

        options = ["In een uur"]

        current_time = datetime.datetime.now().astimezone(TIMEZONE)
        options_datetime = [current_time + datetime.timedelta(hours=1)]
        # In the morning
        if MORNING[0] <= current_time.hour < MORNING[1]:
            options += ["Vanmiddag, om 16:00",
                        "Vanavond, om 21:00",
                        "Morgenochtend om deze tijd"]

            options_datetime += [current_time.replace(hour=16, minute=0, second=0),
                                 current_time.replace(hour=21, minute=0, second=0),
                                 current_time + datetime.timedelta(days=1)]

        # In the afternoon
        elif AFTERNOON[0] <= current_time.hour < AFTERNOON[1]:
            options += ["Vanavond, om 21:00",
                        "Morgenochtend, om 8:00",
                        "Morgenmiddag om deze tijd"]

            options_datetime += [current_time.replace(hour=21, minute=0, second=0),
                                 current_time.replace(hour=8, minute=0, second=0) +
                                                       datetime.timedelta(days=1),
                                 current_time + datetime.timedelta(days=1)]

        # In the evening
        elif EVENING[0] <= current_time.hour < EVENING[1]:
            options += ["Morgenochtend, om 8:00",
                        "Morgenmiddag, om 16:00",
                        "Morgenavond om deze tijd"]

            options_datetime += [current_time.replace(hour=8, minute=0, second=0) +
                                                      datetime.timedelta(days=1),
                                 current_time.replace(hour=16, minute=0, second=0) +
                                                       datetime.timedelta(days=1),
                                 current_time + datetime.timedelta(days=1)]

        # In the night
        else:
            options += ["Vanmiddag, om 16:00",
                        "Vanavond, om 21:00",
                        "Morgen om deze tijd"]

            options_datetime += [current_time.replace(hour=16, minute=0, second=0),
                                 current_time.replace(hour=21, minute=0, second=0),
                                 current_time + datetime.timedelta(days=1)]

        # Create string of options to utter them
        num_options = len(options)
        rescheduling_options_string = ""
        for o in range(num_options):
            rescheduling_options_string += "(" + str(o + 1) + ") " + options[o] + "."
            if not o == len(options) - 1:
                rescheduling_options_string += " "

        return [SlotSet("rescheduling_options_list", options),
                SlotSet("rescheduling_options_string",
                        rescheduling_options_string)]


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