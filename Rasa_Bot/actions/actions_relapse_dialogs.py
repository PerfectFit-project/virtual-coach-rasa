"""
Contains custom actions related to the relapse dialogs
"""
import logging
from typing import Any, Dict, Text

from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from .definitions import REDIS_URL

celery = Celery(broker=REDIS_URL)

# Trigger relapse phase through celery
class TriggerRelapseDialog(Action):
    def name(self):
        return "action_trigger_relapse"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        slot = tracker.get_slot("current_intervention_component")
        logging.info(slot)

        celery.send_task('celery_tasks.relapse_dialog', (user_id, slot))
        logging.info("no celery error")

        return []


class ValidateTwoOptionsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_two_options_form'

    def validate_one_or_two(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate one or two input."""

        logging.info("Performing the action to validate one_or_two_options_form")  # Debug message
        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"one_or_two": None}

        return {"one_or_two": value}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 2):
            return False
        return True


class ActionResetOneOrTwoSlot(Action):
    """Reset one_or_two slot"""

    def name(self):
        return "action_reset_one_or_two_slot"

    logging.info("Performing the action to validate reset_one_or_two_slot")  # debug msg
    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("one_or_two", None)]

class ValidateCraveLapseRelapse(FormValidationAction):
    def name(self) -> Text:
        return 'validate_crave_lapse_relapse_form'

    def validate_crave_lapse_relapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate crave, lapse or relapse input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"crave_lapse_relapse": None}

        return {"crave_lapse_relapse": value}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 3):
            return False
        return True
