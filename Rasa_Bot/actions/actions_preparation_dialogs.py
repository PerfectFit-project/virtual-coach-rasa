"""
Contains custom actions related to the preparation dialogs.
"""

from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import Components


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
        return "action_set_slot_medication_talk_video"

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
