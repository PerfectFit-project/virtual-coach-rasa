"""
Contains custom actions related to the future self dialog
"""
import logging

from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from .definitions import REDIS_URL
from virtual_coach_db.helper.definitions import PreparationInterventionComponents


celery = Celery(broker=REDIS_URL)


# Store last intervention component in database
class MarkDialogAsCompleted(Action):
    def name(self):
        return "mark_dialog_as_completed"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        slot = tracker.get_slot("current_intervention_component")
        logging.info(slot)

        celery.send_task('celery_tasks.intervention_component_completed', (user_id, slot))
        logging.info("no celery error")

        return []


### Slot-setting methods called for rasa to store current intervention component
class SetSlotProfileCreation(Action):
    def name(self):
        return "action_set_slot_profile_creation"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.PROFILE_CREATION)]


class SetSlotMedicationTalk(Action):
    def name(self):
        return "action_set_slot_medication_talk"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.MEDICATION_TALK)]


class SetSlotColdTurkey(Action):
    def name(self):
        return "action_set_slot_cold_turkey"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.COLD_TURKEY)]


class SetSlotPlanQuitStartDate(Action):
    def name(self):
        return "action_set_slot_plan_quit_start_date"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.PLAN_QUIT_START_DATE)]


class SetSlotMentalContrasting(Action):
    def name(self):
        return "action_set_slot_mental_contrasting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.FUTURE_SELF)]


class SetSlotGoalSetting(Action):
    def name(self):
        return "action_set_slot_goal_setting"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component", PreparationInterventionComponents.GOAL_SETTING)]
