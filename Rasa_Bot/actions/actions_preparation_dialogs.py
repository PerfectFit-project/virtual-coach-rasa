"""
Contains custom actions related to the preparation dialogs
"""
from typing import Text, List, Any, Dict
from datetime import datetime
import logging

from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.events import EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from virtual_coach_db.helper.definitions import PreparationInterventionComponents

from virtual_coach_db.helper.helper_functions import get_db_session
from .helper import (store_user_preferences_to_db, get_intervention_component_id)
from virtual_coach_db.dbschema.models import (Users, DialogAnswers, UserInterventionState,
                                              InterventionComponents)

YES_OR_NO = ["yes", "no"]
ALLOWED_WEEK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

### Slot-setting methods called for rasa to store current intervention component
class SetSlotProfileCreation(Action):
    def name(self):
        return "action_set_slot_profile_creation"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.PROFILE_CREATION)]


class SetSlotMedicationTalk(Action):
    def name(self):
        return "action_set_slot_medication_talk"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.MEDICATION_TALK)]


class SetSlotColdTurkey(Action):
    def name(self):
        return "action_set_slot_cold_turkey"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.COLD_TURKEY)]


class SetSlotPlanQuitStartDate(Action):
    def name(self):
        return "action_set_slot_plan_quit_start_date"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.PLAN_QUIT_START_DATE)]


class SetSlotMentalContrasting(Action):
    def name(self):
        return "action_set_slot_mental_contrasting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.FUTURE_SELF)]


class SetSlotGoalSetting(Action):
    def name(self):
        return "action_set_slot_goal_setting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.GOAL_SETTING)]

class ValidateUserPreferencesForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_user_preferences_form"

    def validate_recursive_reminder(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate recursive_reminder` value."""
        logging.info("recursive reminder validation 1")
        if slot_value.lower() not in YES_OR_NO:
            dispatcher.utter_message(text=f"We only accept 'yes' or 'no' as answers")
            return {"recursive_reminder": None}
        dispatcher.utter_message(text=f"OK! You have answered {slot_value}.")
        return {"recursive_reminder": slot_value}

    def validate_week_days(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `week_days` value."""
        logging.info("week days 1")
        if slot_value not in ALLOWED_WEEK_DAYS:
            dispatcher.utter_message(text=f"I don't recognize that day of the week, try again!")
            return {"week_days": None}
        dispatcher.utter_message(text=f"OK! You want to receive reminders on {slot_value}s.")
        return {"week_days": slot_value}

    def validate_time_stamp(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `time_stamp` value."""

        logging.info("timestamp 1")
        timestring = slot_value
        format = "%H:%M:%S"
        res = False

        logging.info("res initialized")
        # using try-except to check for truth value
        try:
            res = bool(datetime.strptime(timestring, format))
            logging.info("res is now: " + str(res))
        except ValueError:
            res = False

        logging.info("after the value error line res is: " + str(res))

        if not res:
            dispatcher.utter_message(text=f"Please submit an answer as given by the example: 20:34:20")
            return {"time_stamp": None}
        dispatcher.utter_message(text=f"OK! You want to receive reminders at {slot_value}.")
        return {"time_stamp": slot_value}

class StoreUserPreferencesToDb(Action):
    def name(self) -> Text:
        return "action_store_user_preferences_to_db"

    async def run(self, dispatcher, tracker, domain):
        logging.info("running custom action StoreUserPreferences to DB")
        ##user_id = tracker.current_state()['sender_id']
        user_id = 41482

        logging.info("user id is: " + str(user_id))

        recursive = tracker.get_slot("recursive_reminder")
        week_days = tracker.get_slot("week_days")
        preferred_time_string = tracker.get_slot("time_stamp")
        logging.info("recursive slot is: " + str(recursive) + ", week days slot is: " + str(week_days) + ", preferred time is: " + str(preferred_time))

        recursive_bool = False
        if recursive == "yes":
            recursive_bool = True

        logging.info("boolean is now: " + str(recursive_bool))

        ##intervention_component_string = tracker.get_slot("current_intervention_component")
        intervention_component = get_intervention_component_id("profile_creation")
        logging.info("storing into db, intervention comp id is: " + str(intervention_component))

        datetime_format = datetime.strptime(preferred_time_string, '%H:%M:%S')
        preferred_time = datetime_format.timestamp()
        logging.info("successfully converted to timestamp, calling helper function")

        store_user_preferences_to_db(user_id, intervention_component, recursive_bool, week_days, preferred_time)
        return