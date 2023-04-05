from . import validator
from .definitions import (DAYPART_NAMES_DUTCH,
                          DAYS_OF_WEEK,
                          PROFILE_CREATION_CONF_SLOTS)
from .helper import (compute_godin_level, 
                     compute_mean_cluster_similarity_ratings, 
                     compute_mean_confidence,
                     compute_preferred_time,
                     get_latest_bot_utterance,
                     store_profile_creation_data_to_db)

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
    

class ValidateProfileCreationCodeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_code_form'

    def validate_profile_creation_code_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_code_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_code_slot':
            return {"profile_creation_code_slot": None}

        if not validator.validate_participant_code(value):
            dispatcher.utter_message(response="utter_profile_creation_code_not_valid")
            return {"profile_creation_code_slot": None}

        return {"profile_creation_code_slot": value}


class ValidateProfileCreationDayTimeConfirmForm(FormValidationAction):
    
    def name(self) -> Text:
        return 'validate_profile_creation_day_time_confirm_form'

    def validate_profile_creation_day_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_day_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_day_slot':
            return {"profile_creation_day_slot": None}
        
        validated, day_name = validator.validate_days_of_week(value)

        if not validated:
            dispatcher.utter_message(response="utter_profile_creation_day_not_valid")
            return {"profile_creation_day_slot": None}
        
        dispatcher.utter_message(response="utter_profile_creation_preference_4")
        dispatcher.utter_message(response="utter_profile_creation_preference_5")

        return {"profile_creation_day_slot": day_name}
    

    def validate_profile_creation_time_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_time_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_time_slot':
            return {"profile_creation_time_slot": None}

        if not validator.validate_number_in_range_response(n_min = 1, n_max = 3, 
                                                           response = value):
            dispatcher.utter_message(response="utter_profile_creation_time_not_valid")
            return {"profile_creation_time_slot": None}
        
        time = int(value)
        daypart = DAYPART_NAMES_DUTCH[time - 1]
        day = tracker.get_slot("profile_creation_day_slot")
        
        message = "Staat genoteerd. Wij gaan de komende tijd steeds op " + day + " " + daypart + " samen in gesprek."
        dispatcher.utter_message(text=message)

        return {"profile_creation_time_slot": time}
    
    
    def validate_profile_creation_confirm_preference_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_confirm_preference_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_confirm_preference_slot':
            return {"profile_creation_confirm_preference_slot": None}

        if not validator.validate_number_in_range_response(n_min = 1, n_max = 2, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"profile_creation_confirm_preference_slot": None}
        
        # User wants to modify something about the timing 
        if value == "2":
            return {"profile_creation_day_slot": None,
                    "profile_creation_time_slot": None,
                    "profile_creation_confirm_preference_slot": None}

        return {"profile_creation_confirm_preference_slot": int(value)}


class ValidateProfileCreationRunWalkForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_run_walk_form'

    def validate_profile_creation_run_walk_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_run_walk_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_run_walk_slot':
            return {"profile_creation_run_walk_slot": None}

        if not validator.validate_number_in_range_response(n_min = 1, n_max = 2, 
                                                           response = value):
            dispatcher.utter_message(response="utter_profile_creation_run_walk_not_valid")
            return {"profile_creation_run_walk_slot": None}

        return {"profile_creation_run_walk_slot": int(value)}


class ValidateProfileCreationGodinLightForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_godin_light_form'

    def validate_profile_creation_godin_light_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_godin_light_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_godin_light_slot':
            return {"profile_creation_godin_light_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 100, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"profile_creation_godin_light_slot": None}

        return {"profile_creation_godin_light_slot": int(value)}
    

class ValidateProfileCreationGodinModerateForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_godin_moderate_form'

    def validate_profile_creation_godin_moderate_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_godin_moderate_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_godin_moderate_slot':
            return {"profile_creation_godin_moderate_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 100, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"profile_creation_godin_moderate_slot": None}

        return {"profile_creation_godin_moderate_slot": int(value)}
    

class ValidateProfileCreationGodinIntensiveForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_godin_intensive_form'

    def validate_profile_creation_godin_intensive_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_godin_intensive_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_godin_intensive_slot':
            return {"profile_creation_godin_intensive_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 100, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"profile_creation_godin_intensive_slot": None}

        return {"profile_creation_godin_intensive_slot": int(value)}
    

class ValidateProfileCreationSim1Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_sim_1_form'

    def validate_profile_creation_sim_1_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_sim_1_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_sim_1_slot':
            return {"profile_creation_sim_1_slot": None}

        if not validator.validate_number_in_range_response(n_min = -3, n_max = 3, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_neg_to_pos_3")
            return {"profile_creation_sim_1_slot": None}

        return {"profile_creation_sim_1_slot": int(value)}


class ValidateProfileCreationSim2Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_sim_2_form'

    def validate_profile_creation_sim_2_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_sim_2_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_sim_2_slot':
            return {"profile_creation_sim_2_slot": None}

        if not validator.validate_number_in_range_response(n_min = -3, n_max = 3, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_neg_to_pos_3")
            return {"profile_creation_sim_2_slot": None}

        return {"profile_creation_sim_2_slot": int(value)}
    
    
class ValidateProfileCreationSim3Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_sim_3_form'

    def validate_profile_creation_sim_3_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_sim_3_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_sim_3_slot':
            return {"profile_creation_sim_3_slot": None}

        if not validator.validate_number_in_range_response(n_min = -3, n_max = 3, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_neg_to_pos_3")
            return {"profile_creation_sim_3_slot": None}

        return {"profile_creation_sim_3_slot": int(value)}
    

class ValidateProfileCreationSim4Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_sim_4_form'

    def validate_profile_creation_sim_4_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_sim_4_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_sim_4_slot':
            return {"profile_creation_sim_4_slot": None}

        if not validator.validate_number_in_range_response(n_min = -3, n_max = 3, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_neg_to_pos_3")
            return {"profile_creation_sim_4_slot": None}

        return {"profile_creation_sim_4_slot": int(value)}
    

class ValidateProfileCreationConf1Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_1_form'

    def validate_profile_creation_conf_1_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_1_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_1_slot':
            return {"profile_creation_conf_1_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_1_slot": None}

        return {"profile_creation_conf_1_slot": int(value)}


class ValidateProfileCreationConf2Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_2_form'

    def validate_profile_creation_conf_2_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_2_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_2_slot':
            return {"profile_creation_conf_2_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_2_slot": None}

        return {"profile_creation_conf_2_slot": int(value)}


class ValidateProfileCreationConf3Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_3_form'

    def validate_profile_creation_conf_3_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_3_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_3_slot':
            return {"profile_creation_conf_3_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_3_slot": None}

        return {"profile_creation_conf_3_slot": int(value)}


class ValidateProfileCreationConf4Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_4_form'

    def validate_profile_creation_conf_4_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_4_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_4_slot':
            return {"profile_creation_conf_4_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_4_slot": None}

        return {"profile_creation_conf_4_slot": int(value)}


class ValidateProfileCreationConf5Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_5_form'

    def validate_profile_creation_conf_5_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_5_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_5_slot':
            return {"profile_creation_conf_5_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_5_slot": None}

        return {"profile_creation_conf_5_slot": int(value)}
   

class ValidateProfileCreationConf6Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_6_form'

    def validate_profile_creation_conf_6_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_6_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_6_slot':
            return {"profile_creation_conf_6_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_6_slot": None}

        return {"profile_creation_conf_6_slot": int(value)}


class ValidateProfileCreationConf7Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_7_form'

    def validate_profile_creation_conf_7_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_7_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_7_slot':
            return {"profile_creation_conf_7_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_7_slot": None}

        return {"profile_creation_conf_7_slot": int(value)}


class ValidateProfileCreationConf8Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_8_form'

    def validate_profile_creation_conf_8_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_8_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_8_slot':
            return {"profile_creation_conf_8_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_8_slot": None}

        return {"profile_creation_conf_8_slot": int(value)}


class ValidateProfileCreationConf9Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_9_form'

    def validate_profile_creation_conf_9_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_9_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_9_slot':
            return {"profile_creation_conf_9_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_9_slot": None}

        return {"profile_creation_conf_9_slot": int(value)}
    

class ValidateProfileCreationConf10Form(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_conf_10_form'

    def validate_profile_creation_conf_10_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_conf_10_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_conf_10_slot':
            return {"profile_creation_conf_10_slot": None}

        if not validator.validate_number_in_range_response(n_min = 0, n_max = 10, 
                                                           response = value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"profile_creation_conf_10_slot": None}

        return {"profile_creation_conf_10_slot": int(value)}


class ProfileCreationSetConfLowHighSlot(Action):
    """Set conf low high slot"""

    def name(self):
        return "profile_creation_set_conf_low_high_slot"

    async def run(self, dispatcher, tracker, domain):
        
        # Find the conf slot we just set
        conf = -1
        for conf_slot in PROFILE_CREATION_CONF_SLOTS:
            conf = tracker.get_slot(conf_slot)
            if conf > -1:
                break
        
        low_high = 0
        if conf > 1:
            low_high = 1
            
        return [SlotSet("profile_creation_conf_low_high_slot", low_high)]


class ProfileCreationSaveToDB(Action):
    """Save profile creation data to database"""

    def name(self):
        return "profile_creation_save_to_db"

    async def run(self, dispatcher, tracker, domain):
    
        user_id = tracker.current_state()['sender_id']
        
        # Compute mean confidence
        conf_avg = compute_mean_confidence(tracker)
        
        # Get the preference for walking or running from slot
        # Deduct 1 since database stores 0 for walking and 1 for running.
        walk_run_pref = tracker.get_slot("profile_creation_run_walk_slot") - 1
        
        # Compute Godin level based on Godin score
        godin_level = compute_godin_level(tracker)
            
        # Compute the perceived similarity for the two clusters of testimonials
        c1_mean, c3_mean = compute_mean_cluster_similarity_ratings(tracker)
        
        # Get preferred day of the week
        day = tracker.get_slot("profile_creation_day_slot")
        day_idx = DAYS_OF_WEEK.index(day) + 1  # Start index at 1 for db
        
        # Get preferred time
        preferred_time = compute_preferred_time(tracker)
        
        # Get participant code
        participant_code = tracker.get_slot("profile_creation_code_slot")
        
        # Store in database
        store_profile_creation_data_to_db(user_id, godin_level, walk_run_pref,
                                          conf_avg, c1_mean, c3_mean, 
                                          participant_code, str(day_idx), 
                                          preferred_time)
        
        return []
