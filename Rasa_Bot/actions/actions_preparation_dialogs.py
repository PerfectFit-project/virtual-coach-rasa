"""
Contains custom actions related to the preparation dialogs
"""
from typing import Text, Any, Dict
from datetime import datetime

from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from virtual_coach_db.helper.definitions import Components

YES_OR_NO = ["yes", "no"]
ALLOWED_WEEK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

### Slot-setting methods called for rasa to store current intervention component


class SetSlotPreparationIntro(Action):
    def name(self):
        return "action_set_slot_preparation_intro"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.PREPARATION_INTRODUCTION)]


class SetSlotProfileCreation(Action):
    def name(self):
        return "action_set_slot_profile_creation"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.PROFILE_CREATION)]


class SetSlotMedicationTalk(Action):
    def name(self):
        return "action_set_slot_medication_talk"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.MEDICATION_TALK)]


class SetSlotTrackBehavior(Action):
    def name(self):
        return "action_set_slot_track_behavior"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.TRACK_BEHAVIOR)]


class SetSlotColdTurkey(Action):
    def name(self):
        return "action_set_slot_cold_turkey"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.COLD_TURKEY)]


class SetSlotPlanQuitStartDate(Action):
    def name(self):
        return "action_set_slot_plan_quit_start_date"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.PLAN_QUIT_START_DATE)]


class SetSlotMentalContrasting(Action):
    def name(self):
        return "action_set_slot_mental_contrasting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.FUTURE_SELF)]


class SetSlotGoalSetting(Action):
    def name(self):
        return "action_set_slot_goal_setting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.GOAL_SETTING)]

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
        # pylint: disable=unused-argument
        """Validate recursive_reminder` value."""
        if slot_value.lower() not in YES_OR_NO:
            dispatcher.utter_message(text="We only accept 'yes' or 'no' as answers")
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
        # pylint: disable=unused-argument
        """Validate `week_days` value."""

        week_days_string = slot_value
        week_days_list = week_days_string.split(", ")
        invalidinput = False

        for weekday in week_days_list:
            if weekday.lower() not in ALLOWED_WEEK_DAYS:
                invalidinput = True

        if invalidinput:
            dispatcher.utter_message(text="Please submit the days of the week as" +
                                          " a comma separated list!")
            return {"week_days": None}
        dispatcher.utter_message(text="OK! You want to receive reminders on these" +
                                      f" days of the week: {slot_value}.")
        return {"week_days": slot_value}

    def validate_time_stamp(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate `time_stamp` value."""

        timestring = slot_value
        timeformat = "%H:%M:%S"
        res = False

        # using try-except to check for truth value
        try:
            res = bool(datetime.strptime(timestring, timeformat))
        except ValueError:
            res = False

        if not res:
            dispatcher.utter_message(text="Please submit an answer as given by the example:" +
                                          " 20:34:20")
            return {"time_stamp": None}
        dispatcher.utter_message(text=f"OK! You want to receive reminders at {slot_value}.")
        return {"time_stamp": slot_value}


class StoreUserPreferencesToDb(Action):
    def name(self) -> Text:
        return "action_store_user_preferences_to_db"

    async def run(self, dispatcher, tracker, domain):
        return []