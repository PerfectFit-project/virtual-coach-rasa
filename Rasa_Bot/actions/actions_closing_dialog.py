from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import (DialogExpectedDuration,
                                                 ExecutionInterventionComponentsTriggers)
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any
from celery import Celery
from . import validator
from .definitions import REDIS_URL, MORNING, AFTERNOON, TIMEZONE
from .helper import get_latest_bot_utterance
from .actions_rescheduling_dialog import get_reschedule_date
import datetime


celery = Celery(broker=REDIS_URL)


class ValidateClosingPaEvaluationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_pa_evaluation_form'

    def validate_closing_pa_evaluation(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate form for evaluation of pa."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_pa_evaluation':
            return {"closing_pa_evaluation": None}

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"closing_pa_evaluation": None}

        return {"closing_pa_evaluation": value}
