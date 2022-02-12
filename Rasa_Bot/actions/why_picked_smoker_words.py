# -*- coding: utf-8 -*-

import logging
import os

from typing import Any, Dict, Text

from rasa_sdk.events import SlotSet
from rasa_sdk.forms import FormValidationAction
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv('DB_HOST')


class ActionResetPickedWordsSlot(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_picked_words_slot"

    async def run(self, dispatcher, tracker, domain):
        logging.warning("running {}".format(type(self)))
        return [SlotSet("picked_words", None)]


class ActionResetHasEnoughWords(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_has_enough_words"

    async def run(self, dispatcher, tracker, domain):
        logging.warning("running {}".format(type(self)))
        return [SlotSet("has_enough_words", None)]


class ActionResetWhyPickedWordsSlotPA(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_why_picked_words_slot_pa"

    async def run(self, dispatcher, tracker, domain):
        logging.warning("running {}".format(type(self)))
        return [SlotSet("why_picked_words", None)]


class ActionResetConfirmWordsResponseSlotSmoking(Action):
    """Reset confirm_words_response slot"""

    def name(self):
        return "action_reset_confirm_words_response_slot_smoking"

    async def run(self, dispatcher, tracker, domain):
        logging.warning("running {}".format(type(self)))
        return [SlotSet("confirm_words_response", None)]


# wvxvw edits
class ActionCountingExplanationWordsSlot(Action):
    """Check has_enough_words_response slot"""

    def name(self):
        return "action_count_why_picked_smoker_words_smoking"

    async def run(self, dispatcher, tracker, domain):
        logging.warning("running {}".format(type(self)))
        return [SlotSet(
            "has_enough_words", 
            len(tracker.latest_message['text'].split()),
        )]


class ValidateCountWordsForm(FormValidationAction):

    def name(self) -> Text:
        return 'validate_why_picked_smoker_words_form'

    def validate_why_picked_smoker_words_response(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate validate_long_enough_response input."""
        logging.warning("running {} with {}".format(type(self), value))
        if not value:
            dispatcher.utter_message("Zou je dat in meer woorden kunnen omschrijven?")

        return {"has_enough_words": value}
