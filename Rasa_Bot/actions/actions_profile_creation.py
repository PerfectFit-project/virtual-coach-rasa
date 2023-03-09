import logging

from . import validator
from .definitions import (DATABASE_URL, DAYS_OF_WEEK_ACCEPTED,
                          NUM_TOP_ACTIVITIES, REDIS_URL)
from .helper import (get_latest_bot_utterance,
                     get_user_intervention_activity_inputs,)

from celery import Celery
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.dbschema.models import (FirstAidKit,
                                              InterventionActivity)
from virtual_coach_db.helper.helper_functions import get_db_session



celery = Celery(broker=REDIS_URL)


def validate_participant_code(code: str):
    
    # Must have length 5
    if len(code) != 5:
        return False
    # Check if code contains only letters and numbers
    if not code.isalnum():
        return False
    # Second and fourth character must be numbers
    if not (code[1].isnumeric() and code[3].isnumeric()):
        return False
    # First, third and fifth character must be letters
    if not (code[0].isalpha() and code[2].isalpha() and code[4].isalpha()):
        return False
    # Number 0 is not used
    if "0" in code:
        return False
    # Second number must be larger than the first
    if not code[3] > code[1]:
        return False
    # Later letters must come later in the alphabet
    if not (code[4].lower() > code[2].lower() and code[2].lower() > code[0].lower()):
        return False
    return True
    

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

        if not validate_participant_code(value):
            dispatcher.utter_message(response="utter_profile_creation_code_not_valid")
            return {"profile_creation_code_slot": None}

        return {"profile_creation_code_slot": value}
    

def validate_days_of_week(value: str):
    for day_name in list(DAYS_OF_WEEK_ACCEPTED.keys()):
        if value in DAYS_OF_WEEK_ACCEPTED[day_name]:
            return True, day_name
    return False, None


class ValidateProfileCreationDayForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_day_form'

    def validate_profile_creation_day_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate profile_creation_day_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_profile_creation_day_slot':
            return {"profile_creation_day_slot": None}
        
        validated, day_name = validate_days_of_week(value)

        if not validated:
            dispatcher.utter_message(response="utter_profile_creation_day_not_valid")
            return {"profile_creation_day_slot": None}

        return {"profile_creation_day_slot": day_name}
    

class ValidateProfileCreationTimeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_time_form'

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

        return {"profile_creation_time_slot": int(value)}


class ProfileCreationMapTimeToDaypart(Action):
    """Map time number to daypart string"""

    def name(self):
        return "profile_creation_map_time_to_daypart"

    async def run(self, dispatcher, tracker, domain):

        time = tracker.get_slot("profile_creation_time_slot")
        
        daypart = "ochtend"
        if time == 2:
            daypart = "middag"
        elif time == 3:
            daypart = "avond"
            
        return [SlotSet("profile_creation_time_daypart_slot", daypart)]


class ValidateProfileCreationConfirmPreferenceForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_profile_creation_confirm_preference_form'

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
        
        
        conf_slots = ["profile_creation_conf_10_slot", "profile_creation_conf_9_slot",
                      "profile_creation_conf_8_slot", "profile_creation_conf_7_slot",
                      "profile_creation_conf_6_slot", "profile_creation_conf_5_slot",
                      "profile_creation_conf_4_slot", "profile_creation_conf_3_slot",
                      "profile_creation_conf_2_slot", "profile_creation_conf_1_slot"]
        
        # Find the conf slot we just set
        conf = -1
        for conf_slot in conf_slots:
            conf = tracker.get_slot(conf_slot)
            if conf > -1:
                break
        
        low_high = 0
        if conf > 1:
            low_high = 1
            
        return [SlotSet("profile_creation_conf_low_high_slot", low_high)]
