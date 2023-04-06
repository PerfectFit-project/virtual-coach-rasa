"""
Contains custom actions related to the weekly reflection dialogue
"""

import datetime
from dateutil.relativedelta import relativedelta
from . import validator
from .definitions import REDIS_URL
from .helper import (get_latest_bot_utterance, get_user,
                     get_user_intervention_state_hrs)
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.helper.definitions import Components

celery = Celery(broker=REDIS_URL)


# Trigger weekly reflection through celery
class TriggerWeeklyReflectionDialog(Action):
    def name(self):
        return "action_trigger_weekly_reflection"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        celery.send_task('celery_tasks.user_trigger_dialog',
                         (user_id, Components.WEEKLY_REFLECTION))

        return []


class SetSlotWeeklyReflection(Action):
    def name(self):
        return "action_set_slot_weekly_reflection"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('current_intervention_component',
                        Components.WEEKLY_REFLECTION)]


class GetLongTermPaGoal(Action):
    def name(self):
        return "action_get_long_term_pa_goal"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        user_info = get_user(user_id)
        pa_goal = user_info.long_term_pa_goal
        return [SlotSet('long_term_pa_goal', pa_goal)]


class UserCompletedHrsSinceLastWeek(Action):
    def name(self):
        return "action_user_completed_hrs"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        intervention_state = get_user_intervention_state_hrs(user_id)

        current_time = datetime.datetime.now()

        for state in intervention_state:
            time_since_complete = relativedelta(current_time, state.last_time).days
            if state.completed and time_since_complete < 7:
                return [SlotSet('completed_hrs', 1)]

        return [SlotSet('completed_hrs', 2)]


class GetWeekNumber(Action):
    def name(self):
        return "action_get_week_number"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        user_info = get_user(user_id)
        exec_week = user_info.execution_week
        if exec_week > 11:
            return [FollowupAction('action_end_dialog')]
        return [SlotSet('week_number', str(exec_week))]


class WhichPaGroup(Action):
    def name(self):
        return "action_which_pa_group"

    async def run(self, dispatcher, tracker, domain):
        ## TODO This method should return the current pa group of the user from the database
        steps_bool = True
        if steps_bool:
            return [SlotSet('pa_group', 1)]
        return [SlotSet('pa_group', 2)]

class SetPaGroup(Action):
    def name(self):
        return "action_set_pa_group"

    async def run(self, dispatcher, tracker, domain):
        ## TODO this method should save in the database the pa group based on steps and set slot
        steps_bool = True
        if steps_bool:
            return [SlotSet('pa_group', 1)]
        return [SlotSet('pa_group', 2)]


class SetStepGoalDays(Action):
    def name(self):
        return "action_set_step_goal_days"

    async def run(self, dispatcher, tracker, domain):
        ## TODO This method should get step goal days and set accordingly
        step_goal_days = 7
        return [SlotSet('step_goal_days', step_goal_days)]

class StepGoalUtterances(Action):
    def name(self):
        return "action_step_goal_utterances"

    async def run(self, dispatcher, tracker, domain):
        ## TODO retrieve amount of days that step goal was met, then set the slot
        step_goal_days = 7
        if step_goal_days > 5:
            dispatcher.utter_message(response="utter_overview_group1_4")
        elif 3 < step_goal_days < 6:
            dispatcher.utter_message(response="utter_overview_group1_5")
            dispatcher.utter_message(response="utter_overview_group1_6")
        else:
            dispatcher.utter_message(response="utter_overview_group1_7")
            dispatcher.utter_message(response="utter_overview_group1_8")

        return []

class SetIntensityMinutes(Action):
    def name(self):
        return "action_set_intensity_minutes"

    async def run(self, dispatcher, tracker, domain):
        ## TODO This method should get minutes and set the slot accordingly
        intensity_minutes = 50
        return [SlotSet('intensity_minutes', intensity_minutes)]

class SetIntensityMinutesGoal(Action):
    def name(self):
        return "action_set_intensity_minutes_goal"

    async def run(self, dispatcher, tracker, domain):
        ## TODO This method should get minutes goal and set the slot accordingly, adding 15 minutes
        intensity_minutes = 50 + 15
        return [SlotSet('intensity_minutes', intensity_minutes)]


class ValidateHowWentNonSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_how_went_non_smoke_form'

    def validate_how_went_non_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_went_non_smoke':
            return {"how_went_non_smoke": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"how_went_non_smoke": None}

        return {"how_went_non_smoke": value}


class ValidateSpecificMomentsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_specific_moments_form'

    def validate_specific_moments(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_specific_moments':
            return {"specific_moments": None}

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"specific_moments": None}

        return {"specific_moments": value}


class ValidateSmokedPreviousWeekForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_smoked_previous_week_form'

    def validate_smoked_previous_week(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_smoked_previous_week':
            return {"smoked_previous_week": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"smoked_previous_week": None}

        return {"smoked_previous_week": value}


class ValidatePossibleSmokingSituationsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_possible_smoking_situations_form'

    def validate_possible_smoking_situations(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_possible_smoking_situations':
            return {"possible_smoking_situations": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"possible_smoking_situations": None}

        return {"possible_smoking_situations": value}


class ValidateHowWentPaForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_how_went_pa_form'

    def validate_how_went_pa(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_went_pa':
            return {"how_went_pa": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"how_went_pa": None}

        return {"how_went_pa": value}


class ValidateDifficultMomentsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_difficult_moments_form'

    def validate_difficult_moments(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_difficult_moments':
            return {"difficult_moments": None}

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"difficult_moments": None}

        return {"difficult_moments": value}


class ValidateRefreshPreviousWeekForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_refresh_previous_week_form'

    def validate_refresh_previous_week(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_refresh_previous_week':
            return {"refresh_previous_week": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_type_1_or_2_difficult_moments")
            return {"refresh_previous_week": None}

        return {"refresh_previous_week": value}


class ValidateMetExpectationsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_met_expectations_form'

    def validate_met_expectations(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_met_expectations':
            return {"met_expectations": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"met_expectations": None}

        return {"met_expectations": value}


class ValidateIfDoableForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_if_doable_form'

    def validate_if_doable(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_if_doable':
            return {"if_doable": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"if_doable": None}

        return {"if_doable": value}


class ValidateDifficultMomentsNextWeekForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_difficult_moments_next_week_form'

    def validate_difficult_moments_next_week(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_difficult_moments_next_week':
            return {"difficult_moments_next_week": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_type_1_2_difficult_moments")
            return {"difficult_moments_next_week": None}

        return {"difficult_moments_next_week": value}


class ValidateFreeReflect1Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_free_reflect_1_form'

    def validate_free_reflect_1(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_free_reflect_1':
            return {"free_reflect_1": None}

        long_enough_response = validator.validate_long_enough_response_words(value, 5)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"free_reflect_1": None}

        return {"free_reflect_1": value}


class ValidateFreeReflect2Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_free_reflect_2_form'

    def validate_free_reflect_2(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_free_reflect_2':
            return {"free_reflect_2": None}

        long_enough_response = validator.validate_long_enough_response_words(value, 5)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"free_reflect_2": None}

        return {"free_reflect_2": value}


class ValidateFreeReflect3Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_free_reflect_3_form'

    def validate_free_reflect_3(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_free_reflect_3':
            return {"free_reflect_3": None}

        long_enough_response = validator.validate_long_enough_response_words(value, 5)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"free_reflect_3": None}

        return {"free_reflect_3": value}


class ValidateFreeReflect4Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_free_reflect_4_form'

    def validate_free_reflect_4(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_free_reflect_4':
            return {"free_reflect_4": None}

        long_enough_response = validator.validate_long_enough_response_words(value, 5)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"free_reflect_4": None}

        return {"free_reflect_4": value}


class ValidateUserReady1Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_user_ready_1_form'

    def validate_user_ready_1(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_user_ready_1':
            return {"user_ready_1": None}

        if value.lower() != "klaar":
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_klaar")
            return {"user_ready_1": None}

        return {"user_ready_1": value}


class ValidateUserReady2Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_user_ready_2_form'

    def validate_user_ready_2(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_user_ready_2':
            return {"user_ready_2": None}

        if value.lower() != "klaar":
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_klaar")
            return {"user_ready_2": None}

        return {"user_ready_2": value}


class ValidateUserReady3Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_user_ready_3_form'

    def validate_user_ready_3(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_user_ready_3':
            return {"user_ready_3": None}

        if value.lower() != "klaar":
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_klaar")
            return {"user_ready_3": None}

        return {"user_ready_3": value}


class ValidateUserReady4Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_user_ready_4_form'

    def validate_user_ready_4(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_user_ready_4':
            return {"user_ready_4": None}

        if value.lower() != "klaar":
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_klaar")
            return {"user_ready_4": None}

        return {"user_ready_4": value}


class ValidateHowAreYou(FormValidationAction):
    def name(self) -> Text:
        return 'validate_how_are_you_form'

    def validate_how_are_you(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_are_you':
            return {"how_are_you": None}

        return {"how_are_you": value}
