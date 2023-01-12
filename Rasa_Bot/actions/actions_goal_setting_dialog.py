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


class ActionGoalSettingContinueAfterPlan(Action):
    def name(self):
        return "action_goal_setting_continue_after_plan"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        current_dialog = tracker.get_slot('current_intervention_component')

        if current_dialog == ExecutionInterventionComponents.RELAPSE_DIALOG:
            # resumes the relapse dialog from rule: smoke relapse decide to get medication info
            dispatcher.utter_message(response="utter_smoke_relapse_8")
            return [FollowupAction('relapse_medication_info_form')]
        elif current_dialog == PreparationInterventionComponents.GOAL_SETTING:
            return [FollowupAction('utter_goal_setting_pa_expl_1')]


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

    def validate_extra_explanation_quiting(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate extra explanation form."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_extra_explanation_quiting':
            return {"extra_explanation_quiting": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"extra_explanation_quiting": None}

        return {"extra_explanation_quiting": value}


class ActionSetSlotGoalSettingDialog(Action):
    def name(self):
        return "action_set_slot_goal_setting_dialog"

    async def run(self, dispatcher, tracker, domain):
        # TODO: check if we need to store user_intervention_state
        # user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        # update the user_intervention_state table
        # store_user_intervention_state(user_id,
        #                               PreparationInterventionComponents.GOAL_SETTING,
        #                               Phases.PREPARATION)

        return [SlotSet('current_intervention_component',
                        PreparationInterventionComponents.GOAL_SETTING)]


class ValidateWhichSportForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_which_sport_form'

    def validate_which_sport(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate which sport form"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_which_sport':
            return {"which_sport": None}

        if not validator.validate_long_enough_response_chars(value, 4):
            dispatcher.utter_message(response="utter_too_few_charachters_sport")
            return {"which_sport": None}

        return {"which_sport": value}


class ValidateFirstPaGoalForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_first_pa_form'

    def validate_which_sport(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate first pa goal form"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_first_pa_goal':
            return {"first_pa_goal": None}

        return {"first_pa_goal": value}


class ValidateTestimonialOneReadForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_testimonial_one_read_form'

    def validate_testimonial_one_read(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate testimonial_one_read_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_testimonial_one_read':
            return {"testimonial_one_read": None}

        if value not in ['Klaar', 'klaar']:
            return {"testimonial_one_read": None}

        return {"testimonial_one_read": value}


class ValidateTestimonialTwoReadForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_testimonial_two_read_form'

    def validate_testimonial_two_read(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate testimonial_two_read_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_testimonial_two_read':
            return {"testimonial_two_read": None}

        if value not in ['Klaar', 'klaar']:
            return {"testimonial_two_read": None}

        return {"testimonial_two_read": value}


class ValidateReadSecondTestimonialForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_read_second_testimonial_form'

    def validate_read_second_testimonial(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate read_second_testimonial."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_read_second_testimonial':
            return {"read_second_testimonial": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"read_second_testimonial": None}

        return {"read_second_testimonial": value}


class ActionContinueTestimonialEvaluation(Action):
    def name(self):
        return "action_continue_testimonial_evaluation"

    async def run(self, dispatcher, tracker, domain):

        return [FollowupAction('utter_test_utter_1')]