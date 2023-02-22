from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from virtual_coach_db.helper.definitions import (DialogExpectedDuration,
                                                 ExecutionInterventionComponentsTriggers)
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any, List, Union
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


class ActionGetSmokingStatus(Action):
    def name(self):
        return "action_closing_get_smoking_status"

    async def run(self, dispatcher, tracker, domain):
        # get smoking status with 1: not (re)lapsed and 2: did (re)lapse last 4 weeks
        smoking_status = 1  # TODO: get this from database
        return [SlotSet('closing_smoking_status', smoking_status)]


class ClosingContinueAfterPa(Action):
    def name(self):
        return "closing_continue_after_pa"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        return [FollowupAction('action_closing_get_smoking_status')]


class ValidateClosingLapseInfoCorrectForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_lapse_info_correct_form'

    def validate_closing_lapse_info_correct(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[str, None]:
        # pylint: disable=unused-argument
        """Validate form whether info on (re)lapse is correct"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_lapse_info_correct':
            return {"closing_lapse_info_correct": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"closing_lapse_info_correct": None}

        if value == 2:
            return {"closing_smoking_status": 2,
                    "closing_lapse_info_correct": value}

        return {"closing_lapse_info_correct": value}


class ValidateClosingReflectionSmokeDoneForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_reflection_smoke_done_form'

    def validate_closing_reflection_smoke_done(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate goal_setting_plan_finished"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_reflection_smoke_done':
            return {"closing_reflection_smoke_done": None}

        if value not in ['Klaar', 'klaar']:
            return {"closing_reflection_smoke_done": None}

        return {"closing_reflection_smoke_done": value}


class ValidateClosingRelapsePreventionPlanOneDoneForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_relapse_prevention_plan_one_done_form'

    def validate_closing_relapse_prevention_plan_one_done(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate goal_setting_plan_finished"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_relapse_prevention_plan_one_done':
            return {"closing_relapse_prevention_plan_one_done": None}

        if value not in ['Klaar', 'klaar']:
            return {"closing_relapse_prevention_plan_one_done": None}

        return {"closing_relapse_prevention_plan_one_done": value}


class ValidateClosingRelapsePreventionPlanTwoDoneForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_relapse_prevention_plan_two_done_form'

    def validate_closing_relapse_prevention_plan_two_done(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate goal_setting_plan_finished"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_relapse_prevention_plan_two_done':
            return {"closing_relapse_prevention_plan_two_done": None}

        if value not in ['Klaar', 'klaar']:
            return {"closing_relapse_prevention_plan_two_done": None}

        return {"closing_relapse_prevention_plan_two_done": value}


class ClosingContinueAfterSmoke(Action):
    def name(self):
        return "closing_continue_after_smoke"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        return [FollowupAction('utter_closing_closing_1')]


class ValidateClosingEvaluatePfForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_closing_evaluate_pf_form'

    def validate_closing_pf_grade(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate closing pf grade"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_pf_grade':
            return {"closing_pf_grade": None}

        if not validator.validate_number_in_range_response(1, 10, value):
            dispatcher.utter_message(response="utter_please_answer_pf_eval")
            return {"closing_pf_grade": None}

        dispatcher.utter_message(text="Dankjewel!")
        return {"closing_pf_grade": value}

    def validate_closing_pf_evaluate(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pf evaluate"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_closing_pf_evaluate':
            return {"closing_pf_evaluate": None}

        return {"closing_pf_evaluate": value}
