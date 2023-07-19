"""
Contains custom actions related to the weekly reflection dialogue
"""

import datetime
from dateutil.relativedelta import relativedelta
from . import validator
from .definitions import REDIS_URL
from .helper import (get_intensity_minutes_goal,
                     get_intervention_component_id,
                     get_last_completed_dialog_part_from_db,
                     get_latest_bot_utterance,
                     get_pa_group,
                     get_steps_data,
                     get_step_goals_and_steps,
                     get_user,
                     get_user_intervention_state_hrs,
                     make_step_overview,
                     set_pa_group_to_db,
                     store_dialog_part_to_db)
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.helper.definitions import Components
import logging


celery = Celery(broker=REDIS_URL)


class ActionSaveWeeklyReflectionDialogPart1(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part1"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 1)

        return []
    
    
class ActionSaveWeeklyReflectionDialogPart2(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part2"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 2)

        return []
    

class ActionSaveWeeklyReflectionDialogPart3(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part3"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 3)

        return []
    
    
class ActionSaveWeeklyReflectionDialogPart4(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part4"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 4)

        return []
    
    
class ActionSaveWeeklyReflectionDialogPart5(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part5"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 5)

        return []
    
    
class ActionSaveWeeklyReflectionDialogPart6(Action):
    """To save first part of weekly-reflection dialog"""

    def name(self):
        return "action_save_weekly_reflection_dialog_part6"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.WEEKLY_REFLECTION), 
                                part = 0)

        return []
    

class ActionGetLastCompletedWeeklyReflectionPart(Action):
    def name(self):
        return "action_get_last_completed_weekly_reflection_part"

    async def run(self, dispatcher, tracker, domain):
        
        user_id = tracker.current_state()['sender_id']
        comp_id = get_intervention_component_id(Components.WEEKLY_REFLECTION)

        # Return value can be -1, 1, 2, 3, 4, or 5
        last_part = get_last_completed_dialog_part_from_db(user_id, 
                                                           comp_id)

        return [SlotSet('last_completed_weekly_reflection_dialog_part',
                last_part)]


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
        user_id = int(tracker.current_state()['sender_id'])

        pa_group = get_pa_group(user_id)

        if pa_group is None:
            pa_group = 2

        return [SlotSet('pa_group', pa_group)]


class SetPaGroup(Action):
    def name(self):
        return "action_set_pa_group"

    async def run(self, dispatcher, tracker, domain):
        # Get user id and set constants
        user_id = int(tracker.current_state()['sender_id'])
        group_2_threshold_total_steps = 56000
        sufficient_daily_steps = 8000
        group_2_threshold_daily_steps = 4

        # Get steps data last 7 days
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=7)
        steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=end)

        total_steps = sum(day['steps'] for day in steps_data)
        daily_steps = sum((day['steps'] >= sufficient_daily_steps) for day in steps_data)

        if (total_steps >= group_2_threshold_total_steps) and\
                (daily_steps >= group_2_threshold_daily_steps):
            pa_group = 2

        else:
            pa_group = 1

        set_pa_group_to_db(user_id, pa_group)

        return [SlotSet('pa_group', pa_group)]


class SetStepGoalDays(Action):
    def name(self):
        return "action_set_step_goal_days"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])

        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=16)
        steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=end)

        _, _, _, step_goal_days = get_step_goals_and_steps(steps_data, start, end)

        if step_goal_days is None:
            dispatcher.utter_message(response="Er is iets mis met de data. Contact de onderzoeker")
            logging.error('User id: %i, dialog: weekly reflection,'
                          'action: action_set_step_goals' % user_id)
            return [SlotSet('step_goal_days', 0)]

        return [SlotSet('step_goal_days', step_goal_days)]


class StepGoalUtterances(Action):
    def name(self):
        return "action_step_goal_utterances"

    async def run(self, dispatcher, tracker, domain):
        step_goal_days = tracker.current_state()['step_goal_days']
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

        user_id = int(tracker.current_state()['sender_id'])

        # get the intensive minutes goal for the previous week
        previous_goal = get_intensity_minutes_goal(user_id)

        # the first time, it's set to 15 minutes
        if previous_goal is None:
            previous_goal = 15

        # the new goal is the previous one, plus 15 minutes
        intensity_minutes = previous_goal + 15

        # save the new goal to the DB

        #TODO: save to db new value
        # set_intensity_minutes_goal(user_id, intensity_minutes)

        return [SlotSet('intensity_minutes_goal', intensity_minutes)]


class ShowPaOverview(Action):
    def name(self):
        return "action_show_pa_overview"

    async def run(self, dispatcher, tracker, domain):
        # Get data from API
        user_id = int(tracker.current_state()['sender_id'])
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=16)
        steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=end)

        # Get steps, goals and dates
        step_goal, step_array, date_array, _ = get_step_goals_and_steps(steps_data, start, end)

        if date_array is None:
            logging.error('user id: %i, dialog: weekly reflection,'
                          'action: action_show_pa_overview' % user_id)
            default_error_image = 'app/pa_overview_error.PNG'  # TODO: add this image
            return [SlotSet("upload_file_path", default_error_image)]

        fig = make_step_overview(date_array, step_array, step_goal)

        filepath = '/app/pa_overview.PNG'

        try:
            fig.write_image("pa_overview.PNG")
        except Exception:
            logging.info("File upload unsuccessful.")

        return [SlotSet("upload_file_path", filepath)]


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
            dispatcher.utter_message(response="utter_answer_1_5_weekly_reflection")
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
            dispatcher.utter_message(response="utter_answer_1_3_weekly_reflection")
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

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_answer_1_3_smoked_prev_week")
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
            dispatcher.utter_message(response="utter_answer_1_2_weekly_reflection")
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
            dispatcher.utter_message(response="utter_answer_1_5_weekly_reflection_pa")
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
            dispatcher.utter_message(response="utter_answer_1_3_weekly_reflection")
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
            dispatcher.utter_message(response="utter_type_1_or_2_difficult_moments")
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
            dispatcher.utter_message(response="utter_answer_more_characters_weekly_reflection")
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
            dispatcher.utter_message(response="utter_answer_more_characters_weekly_reflection")
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

        long_enough_response = validator.validate_long_enough_response_chars(value, 15)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_answer_more_characters_weekly_reflection")
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

        if not validator.validate_klaar(value):
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

        if not validator.validate_klaar(value):
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

        if not validator.validate_klaar(value):
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

        if not validator.validate_klaar(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_klaar")
            return {"user_ready_4": None}

        return {"user_ready_4": value}


class ValidateHaveEquipment(FormValidationAction):
    def name(self) -> Text:
        return 'validate_have_equipment_form'

    def validate_have_equipment(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_have_equipment':
            return {"have_equipment": None}

        if not validator.validate_klaar(value):
            dispatcher.utter_message(response="utter_answer_klaar")
            return {"have_equipment": None}

        return {"have_equipment": value}


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
