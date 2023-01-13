"""
Contains custom actions related to the execution dialogs
"""

from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import ExecutionInterventionComponents


### Slot-setting methods called for rasa to store current intervention component
class SetSlotExecutionIntroduction(Action):
    def name(self):
        return "action_set_slot_execution_introduction"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.EXECUTION_INTRODUCTION)]


class SetSlotGeneralActivity(Action):
    def name(self):
        return "action_set_slot_general_activity"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.GENERAL_ACTIVITY)]


class SetSlotWeeklyReflection(Action):
    def name(self):
        return "action_set_slot_weekly_reflection"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.WEEKLY_REFLECTION)]


class SetSlotDailyReflection(Action):
    def name(self):
        return "action_set_slot_daily_reflection"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.DAILY_REFLECTION)]


class SetSlotRelapseDialog(Action):
    def name(self):
        return "action_set_slot_relapse_dialog"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.RELAPSE_DIALOG)]
