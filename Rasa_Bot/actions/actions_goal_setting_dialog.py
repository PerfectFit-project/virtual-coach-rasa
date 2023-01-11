"""
Contains custom actions related to the relapse dialogs
"""
from virtual_coach_db.helper import ExecutionInterventionComponents, PreparationInterventionComponents

from . import validator
from .definitions import TIMEZONE
from .helper import (get_latest_bot_utterance)
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text


class ActionGetFirstLastDate(Action):
    def name(self):
        return "action_get_first_last_date"

    async def run(self, dispatcher, tracker, domain):
        # get the first (tomorrow) and last (11 days from today) possible quit date
        today = datetime.today().astimezone(TIMEZONE).date()
        first_date = (today + timedelta(days=1)).strftime('%d-%m-%Y')
        last_date = (today + timedelta(days=11)).strftime('%d-%m-%Y')

        return [SlotSet('first_possible_quit_date', first_date),
                SlotSet('last_possible_quit_date', last_date)]


class GoalSettingContinueAfterPlan(Action):
    def name(self):
        return "goal_setting_continue_after_plan"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        current_dialog = tracker.get_slot('current_intervention_component')

        if current_dialog == ExecutionInterventionComponents.RELAPSE_DIALOG_RELAPSE:
            # resumes the relapse dialog from rule: smoke relapse decide to get medication info
            dispatcher.utter_message(response="utter_smoke_relapse_8")
            return [FollowupAction('relapse_medication_info_form')]
        elif current_dialog == PreparationInterventionComponents.GOAL_SETTING:
            # TODO: change to the actual action once implemented
            return [FollowupAction('utter_test_utterance')]


class ValidateChosenQuitDateForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_chosen_quit_date_form'

    def validate_chosen_quit_date_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate chosen_quit_date_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_chosen_quit_date_slot':
            return {"chosen_quit_date_slot": None}

        start_date = tracker.get_slot('first_possible_quit_date')
        stop_date = tracker.get_slot('last_possible_quit_date')

        if not (validator.validate_date_format(value) and validator.validate_date_range(value, start_date, stop_date)):
            dispatcher.utter_message(response="utter_goal_setting_wrong_date")
            return {"chosen_quit_date_slot": None}

        return {"chosen_quit_date_slot": value}


class ValidateGoalSettingPlanFinishedForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_goal_setting_plan_finished_form'

    def validate_goal_setting_plan_finished_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate goal_setting_plan_finished_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_goal_setting_plan_finished_slot':
            return {"goal_setting_plan_finished_slot": None}

        if value not in ['Klaar', 'klaar']:
            return {"goal_setting_plan_finished_slot": None}

        return {"goal_setting_plan_finished_slot": value}


class ValidateHowDoingForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_how_doing_form'

    def validate_how_doing_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate how_doing_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_doing_slot':
            return {"how_doing_slot": None}

        return {"how_doing_slot": value}


class ValidateExtraExlplanationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_extra_explanation_form'

    def validate_extra_explanation(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate extra explanation form."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_extra_explanation_quiting':
            return {"extra_explanation": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"extra_explanation": None}

        return {"extra_explanation": value}