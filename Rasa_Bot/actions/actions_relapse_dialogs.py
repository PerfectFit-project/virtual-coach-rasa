"""
Contains custom actions related to the relapse dialogs
"""
import string
import requests
from .helper import get_latest_bot_utterance
import logging
from typing import Any, Dict, Text

from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from virtual_coach_db.helper.definitions import ExecutionInterventionComponents
from .definitions import REDIS_URL

celery = Celery(broker=REDIS_URL)


class SetSlotRelapseDialog(Action):
    def name(self):
        return "action_set_slot_relapse_dialog"

    async def run(self, dispatcher, tracker, domain):
        print(ExecutionInterventionComponents.RELAPSE_DIALOG)
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.RELAPSE_DIALOG)]


def validate_long_enough_response(response):
    if response is None:
        return False
    return len(simple_sanitize_input(response).split()) > 5


def simple_sanitize_input(value):
    return value.translate({c: "" for c in string.punctuation})


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


class ValidateSmokeOrPaForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_smoke_or_pa_form'

    def validate_smoke_or_pa(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate smoke or pa input."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_smoke_or_pa':
            return {"smoke_or_pa": None}

        logging.info("Performing the action to validate smoke_or_pa_form")  # Debug message
        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"smoke_or_pa": None}

        return {"smoke_or_pa": value}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 2):
            return False
        return True


class ValidateCraveLapseRelapseForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_crave_lapse_relapse_form'

    def validate_crave_lapse_relapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate crave, lapse or relapse input."""
        logging.info("Performing the action to validate crave lapse relapse form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_crave_lapse_relapse':
            return {"crave_lapse_relapse": None}

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


class ValidateEhboMeSelfForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_ehbo_me_self_form'

    def validate_ehbo_me_self(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate ehbo, me or self input"""

        logging.info("Validate ehbo me self form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_ehbo_me_self':
            return {"ehbo_me_self": None}

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"ehbo_me_self": None}

        return {"ehbo_me_self": value}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 3):
            return False
        return True


class ValidateTypeAndNumberSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_type_and_number_smoke_form'

    def validate_type_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input"""

        logging.info("Validate type smoke form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke':
            return {"type_smoke": None}

        if not self._is_valid_input_type(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"type_smoke": None}

        return {"type_smoke": value}

    def validate_type_smoke_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input confirmation"""

        logging.info("Validate type smoke form confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke_confirm':
            return {"type_smoke_confirm": None}

        if not self._is_valid_input_yes_no(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"type_smoke_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"type_smoke": None, "type_smoke_confirm": None}
        else:
            return {"type_smoke_confirm": value}

    def validate_number_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smokes"""

        logging.info("Validate type number smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke':
            return {"number_smoke": None}

        if not self._is_valid_input_number(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"number_smoke": None}

        return {"number_smoke": value}

    def validate_number_smoke_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smoke input confirmation"""

        logging.info("Validate number smoke form confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke_confirm':
            return {"number_smoke_confirm": None}

        if not self._is_valid_input_yes_no(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"number_smoke_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"number_smoke": None, "number_smoke_confirm": None}
        else:
            return {"number_smoke_confirm": value}

    @staticmethod
    def _is_valid_input_number(value):
        try:
            value = int(value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _is_valid_input_type(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 4):
            return False
        return True

    @staticmethod
    def _is_valid_input_yes_no(value):
        if value.lower() in ['Ja', 'ja', 'ja.', 'Nee', 'nee', "nee."]:
            return True
        else:
            return False


class ValidateWhatDoingHowFeelSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_what_doing_how_feel_smoke_form'

    def validate_what_doing_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate what doing while smoking"""
        max_val = 7
        logging.info("Validate what doing smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_what_doing_smoke':
            return {"what_doing_smoke": None}

        value = self._input_to_list(value, max_val)

        if value is False:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"what_doing_smoke": None}

        return {"what_doing_smoke": value}

    def validate_how_feel_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input confirmation"""
        max_val = 5
        logging.info("Validate how feel smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_feel_smoke':
            return {"how_feel_smoke": None}

        value = self._input_to_list(value, max_val)

        if value is False:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"how_feel_smoke": None}

        return {"how_feel_smoke": value}

    @staticmethod
    def _input_to_list(value, max_val):
        try:
            value = list(map(int, value.split()))
        except ValueError:
            return False
        else:
            if min(value) < 0 or max(value) > max_val:
                return False
            else:
                return value


class ValidateWithWhomEventSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_with_whom_event_smoke_form'

    def validate_with_whom_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate with whom smoke """
        max_val = 6
        logging.info("Validate with whom smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_with_whom_smoke':
            return {"with_whom_smoke": None}

        value = self._input_to_list(value, max_val)

        if value is False:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"with_whom_smoke": None}

        return {"with_whom_smoke": value}

    def validate_event_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate event smoke"""
        logging.info("Validate event smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_event_smoke':
            return {"with_whom_smoke": None}

        return {"with_whom_smoke": value}

    @staticmethod
    def _input_to_list(value, max_val):
        try:
            value = list(map(int, value.split()))
        except ValueError:
            return False
        else:
            if min(value) < 0 or max(value) > max_val:
                return False
            else:
                return value


class ValidateReflectBarChartForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_reflect_bar_chart_form'

    def validate_reflect_bar_chart(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate reflect bar chart"""
        logging.info("Validate with whom smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_reflect_bar_chart':
            return {"reflect_bar_chart": None}

        long_enough_response = validate_long_enough_response(value)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"reflect_bar_chart": None}

        return {"reflect_bar_chart": value}


class ValidateTypeAndNumberSmokeRelapseForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_type_and_number_smoke_relapse_form'

    def validate_type_smoke_relapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input relapse"""

        logging.info("Validate type smoke relapse form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke_relapse':
            return {"type_smoke_relapse": None}

        if not self._is_valid_input_type(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"type_smoke_relapse": None}

        return {"type_smoke_relapse": value}

    def validate_type_smoke_relapse_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input relapse confirmation"""

        logging.info("Validate type smoke form relapse confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke_relapse_confirm':
            return {"type_smoke_relapse_confirm": None}

        if not self._is_valid_input_yes_no(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"type_smoke_relapse_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"type_smoke_relapse": None, "type_smoke_relapse_confirm": None}
        else:
            return {"type_smoke_relapse_confirm": value}

    def validate_number_smoke_relapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of relapse smokes"""

        logging.info("Validate type number relapse smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke_relapse':
            return {"number_smoke_relapse": None}

        if not self._is_valid_input_number(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"number_smoke_relapse": None}

        return {"number_smoke_relapse": value}

    def validate_number_smoke_relapse_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smoke input relapse confirmation"""

        logging.info("Validate number smoke form relapse confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke_relapse_confirm':
            return {"number_smoke_relapse_confirm": None}

        if not self._is_valid_input_yes_no(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"number_smoke_relapse_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"number_smoke_relapse": None, "number_smoke_relapse_confirm": None}
        else:
            return {"number_smoke_relapse_confirm": value}

    @staticmethod
    def _is_valid_input_number(value):
        try:
            value = int(value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _is_valid_input_type(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 3):
            return False
        return True

    @staticmethod
    def _is_valid_input_yes_no(value):
        if value.lower() in ['Ja', 'ja', 'ja.', 'Nee', 'nee', "nee."]:
            return True
        else:
            return False


class ValidatePaTypeTogetherWhyFailForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_type_together_why_fail_form'

    def validate_pa_type(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_type"""
        logging.info("Validate type smoke relapse form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_type':
            return {"pa_type": None}

        return {"pa_type": value}

    def validate_pa_together(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_ together"""
        logging.info("Validate type pa together")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_together':
            return {"pa_together": None}

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"pa_together": None}

        return {"pa_together": value}

    def validate_pa_why_fail(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa why fail"""
        max_val = 7
        logging.info("Validate pa why fail")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_why_fail':
            return {"pa_why_fail": None}

        value = self._input_to_list(value, max_val)

        if value is False:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"pa_why_fail": None}

        return {"pa_why_fail": value}

    @staticmethod
    def _input_to_list(value, max_val):
        try:
            value = list(map(int, value.split()))
        except ValueError:
            return False
        else:
            if min(value) < 0 or max(value) > max_val:
                return False
            else:
                return value

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 2):
            return False
        return True
