"""
Contains custom actions related to the relapse dialogs
"""
from virtual_coach_db.dbschema.models import (Testimonials, 
                                              Users)
from virtual_coach_db.helper.definitions import Components
from virtual_coach_db.helper.helper_functions import get_db_session
from . import validator
from .definitions import DATABASE_URL, FILE_PATH_IMAGE_PA, TIMEZONE
from .helper import (get_goal_setting_chosen_sport_from_db,
                     get_intervention_component_id, 
                     get_last_completed_dialog_part_from_db,
                     get_latest_bot_utterance, 
                     store_dialog_part_to_db,
                     store_goal_setting_chosen_sport_to_db,
                     store_long_term_pa_goal_to_db,
                     store_quit_date_to_db)
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text


class ActionSaveGoalSettingDialogPart1(Action):
    """To save first part of goal-setting dialog"""

    def name(self):
        return "action_save_goal_setting_dialog_part1"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.GOAL_SETTING), 
                                part = 1)

        return []
    

class ActionSaveGoalSettingDialogPart2(Action):
    """To save second part of goal-setting dialog"""

    def name(self):
        return "action_save_goal_setting_dialog_part2"

    async def run(self, dispatcher, tracker, domain):
        
        user_id = tracker.current_state()['sender_id']

        store_dialog_part_to_db(user_id, 
                                get_intervention_component_id(Components.GOAL_SETTING), 
                                part = 2)
        
        # Also need to store the "which_sport"-slot to the database
        store_goal_setting_chosen_sport_to_db(user_id, 
                                              tracker.get_slot('which_sport'))

        return []
    

class ActionSaveGoalSettingDialogPart3(Action):
    """To save third part of goal-setting dialog"""

    def name(self):
        return "action_save_goal_setting_dialog_part3"

    async def run(self, dispatcher, tracker, domain):

        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.GOAL_SETTING), 
                                part = 3)

        return []
    

class ActionSaveGoalSettingDialogPart4(Action):
    """To save 4th part of goal-setting dialog"""

    def name(self):
        return "action_save_goal_setting_dialog_part4"

    async def run(self, dispatcher, tracker, domain):

        # 0 means that the entire dialog is completed
        store_dialog_part_to_db(tracker.current_state()['sender_id'], 
                                get_intervention_component_id(Components.GOAL_SETTING), 
                                part = 0)

        return []


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
    
    
def goal_setting_testimonial_model_output(t, user_se: float, user_godin: int, 
                                          user_c1: float, user_c3: float):
    """
    Get the output of the linear regression model used to predict motivation
    ratings of testimonials that differs per testimonial.
    We do not consider the model terms that do not differ between testimonials
    as they do not impact which testimonial is chosen.
    The model is a simplified version of the one developed in this
    paper: https://doi.org/10.1007/s10916-022-01899-9.
    The simplification was done to reduce the number of variables we need
    to collect data on.

    Args:
        t (object from Testimonials table): testimonial
        user_se (float): user self-efficacy
        user_godin (int): user godin activity level
        user_c1 (float): user similarity rating for cluster 1
        user_c3 (float): user similarity rating for cluster 3
    
    Returns:
        float: model output based on testimonial and user (i.e., motivational impact)
        
    """

    t_godin = t.godin_activity_level  # godin level of person providing testimonial
    t_se = t.self_efficacy_pref  # self-efficacy of person providing testimonial
    t_poc1 = int(t.part_of_cluster1)  # whether testimonial is part of cluster 1
    t_poc3 = int(t.part_of_cluster3)  # whether testimonial is part of cluster 3

    # Need to divide by 100 and 2 for scaling to interval [0, 1] for
    # self-efficacy and godin activity level.
    # Cluster ratings are not scaled to [0, 1] in the model.
    model_sim = -1.00491 * abs(user_se - t_se)/100 -0.93247 * abs(user_godin - t_godin)/2 
    model_cluster_member = -0.72352 * t_poc1 - 1.16833 * t_poc3
    model_cluster_inter = 0.26407 * user_c1 * t_poc1 + 0.30176 * user_c3 * t_poc3

    return  model_cluster_member + model_cluster_inter + model_sim
    
    
class ActionGoalSettingChooseTestimonials(Action):
    def name(self):
        return "action_goal_setting_choose_testimonials"

    async def run(self, dispatcher, tracker, domain):

        # Get user ID
        user_id = tracker.current_state()['sender_id']

        # Create session object to connect db
        session = get_db_session(db_url=DATABASE_URL)

        selected = session.query(Users).filter_by(nicedayuid=user_id).one()

        # Get self-efficacy, cluster ratings, and godin activity level of user
        user_se = selected.testim_self_efficacy_pref
        user_c1 = selected.testim_sim_cluster_1
        user_c3 = selected.testim_sim_cluster_3
        user_godin = selected.testim_godin_activity_level

        # Get all testimonials from database
        selected = session.query(Testimonials).all()
        # Compute motivation rating (i.e., model output) for each testimonial
        motiv_all = [goal_setting_testimonial_model_output(t, 
                                                           user_se, 
                                                           user_godin, 
                                                           user_c1, 
                                                           user_c3) for t in selected]

        # Sort testimonials based on motivation rating since we want the 
        # 2 most motivating testimonials
        motiv_all_sorted = sorted(range(len(motiv_all)), 
                                  key=lambda k: motiv_all[k],
                                  reverse = True)

        return [SlotSet('goal_setting_testimonial_1',
                selected[motiv_all_sorted[0]].testimonial_text),
                SlotSet('goal_setting_testimonial_2',
                selected[motiv_all_sorted[1]].testimonial_text)]


class ActionGoalSettingContinueAfterPlan(Action):
    def name(self):
        return "action_goal_setting_continue_after_plan"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        current_dialog = tracker.get_slot('current_intervention_component')

        if current_dialog == Components.RELAPSE_DIALOG:
            # resumes the relapse dialog from rule: smoke relapse decide to get medication info
            dispatcher.utter_message(response="utter_smoke_relapse_8")
            return [FollowupAction('relapse_medication_info_form')]

        if current_dialog == Components.GOAL_SETTING:
            return [FollowupAction('utter_goal_setting_pa_expl_1')]

        return None


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

        if (not (validator.validate_date_format(value)
                 and validator.validate_date_range(value, start_date, stop_date))):
            dispatcher.utter_message(response="utter_goal_setting_wrong_date")
            return {"chosen_quit_date_slot": None}

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        store_quit_date_to_db(user_id, value)
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

        if not validator.validate_klaar(value):
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

        return [SlotSet('current_intervention_component',
                        Components.GOAL_SETTING)]
    

class ActionGetLastCompletedGoalSettingPart(Action):
    def name(self):
        return "action_get_last_completed_goal_setting_part"

    async def run(self, dispatcher, tracker, domain):
        
        user_id = tracker.current_state()['sender_id']
        comp_id = get_intervention_component_id(Components.GOAL_SETTING)

        # Return value can be -1, 1, 2, or 3.
        last_part = get_last_completed_dialog_part_from_db(user_id, 
                                                           comp_id)

        # Need to set which_sport_continue_dialog slot in case last completed 
        # part was 2 or 3.
        # This is because {which_sport} is included in utterances.
        # Since the which_sport-slot is set as part of a form, we created
        # an alternative slot, which_sport_continue_dialog, that is used in
        # the utterances where needed using conditional response variations.
        if last_part in {2, 3}:
            which_sport = get_goal_setting_chosen_sport_from_db(user_id)
            
            return [SlotSet('last_completed_goal_setting_dialog_part',
                    last_part),
                    SlotSet('which_sport_continue_dialog', which_sport)]

        return [SlotSet('last_completed_goal_setting_dialog_part',
                last_part)]


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
        return 'validate_first_pa_goal_form'

    def validate_first_pa_goal(
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

        if not validator.validate_klaar(value):
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

        if not validator.validate_klaar(value):
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

        return [FollowupAction('testimonial_evaluation_form')]


class ValidateTestimonialEvaluationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_testimonial_evaluation_form'

    def validate_testimonial_evaluation(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate testimonial evaluation"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_testimonial_evaluation':
            return {"testimonial_evaluation": None}

        if not validator.validate_long_enough_response_chars(value, 15):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"testimonial_evaluation": None}

        return {"testimonial_evaluation": value}
    
    
class ValidateSecondPaGoalForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_second_pa_goal_form'

    def validate_second_pa_goal(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate second pa goal form"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_second_pa_goal':
            return {"second_pa_goal": None}

        if not validator.validate_long_enough_response_chars(value, 20):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"second_pa_goal": None}

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        store_long_term_pa_goal_to_db(user_id, value)
        return {"second_pa_goal": value}


class ValidateWhyPaGoalImportantForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_why_pa_goal_important_form'

    def validate_why_pa_goal_important_values(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate why_pa_goal_important_values"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_why_pa_goal_important_values':
            return {"why_pa_goal_important_values": None}

        if not validator.validate_number_in_range_response(1, 6, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"why_pa_goal_important_values": None}

        dispatcher.utter_message(response="utter_second_testimonial_11")
        return {"why_pa_goal_important_values": value}

    def validate_why_pa_goal_important_nuance(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate why_pa_goal_important_nuance"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_why_pa_goal_important_nuance':
            return {"why_pa_goal_important_nuance": None}

        if not validator.validate_long_enough_response_chars(value, 15):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"why_pa_goal_important_nuance": None}

        return {"why_pa_goal_important_nuance": value}


class ValidatePaGoalReachableForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_goal_reachable_form'

    def validate_pa_goal_reachable(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_goal_reachable"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_goal_reachable':
            return {"pa_goal_reachable": None}

        if not validator.validate_list(value, 1, 3):
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"pa_goal_reachable": None}

        return {"pa_goal_reachable": value}


class ActionContinueChangePaGoal(Action):
    def name(self):
        return "action_continue_change_pa_goal"

    async def run(self, dispatcher, tracker, domain):

        return [FollowupAction('utter_second_testimonial_18')]


class ValidateRefineSecondPaGoalForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_refine_second_pa_goal_form'

    def validate_refine_second_pa_goal(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate refine second pa goal form"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_refine_second_pa_goal':
            return {"refine_second_pa_goal": None}

        if not validator.validate_long_enough_response_chars(value, 20):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"refine_second_pa_goal": None}

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        store_long_term_pa_goal_to_db(user_id, value)
        return {"refine_second_pa_goal": value}


class ActionContinueStepGoalPa(Action):
    def name(self):
        return "action_continue_step_goal_pa"

    async def run(self, dispatcher, tracker, domain):

        return [FollowupAction('action_save_goal_setting_dialog_part3')]


class ValidateFinishedWritingPaForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_finished_writing_pa_form'

    def validate_finished_writing_pa(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate finished_writing_pa slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_finished_writing_pa':
            return {"finished_writing_pa": None}

        if not validator.validate_klaar(value):
            return {"finished_writing_pa": None}

        return {"finished_writing_pa": value}


class SetFilePathPaImage(Action):
    def name(self):
        return "action_set_file_path_pa_image"

    async def run(self, dispatcher, tracker, domain):

        filepath = FILE_PATH_IMAGE_PA

        return[SlotSet("upload_file_path", filepath)]
