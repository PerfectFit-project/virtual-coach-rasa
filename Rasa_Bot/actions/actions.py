# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.events import ConversationResumed
from rasa_sdk.events import UserUtteranceReverted
from rasa_sdk.events import FollowupAction
    
# Get the user's name from the database.
# Save the extracted name to a slot.
class GetNameFromDatabase(Action):
    def name(self):
        return "action_get_name_from_database"

    async def run(self, dispatcher, tracker, domain):
        
        name = "Kees"
        
        return [SlotSet("name", name)]
    
# Get weekly plan
class GetPlanWeek(Action):
    def name(self):
        return "action_get_plan_week"

    async def run(self, dispatcher, tracker, domain):
        
        plan = "Sure, you should do 2 half-hour running sessions. And please read through this psycho-education: www.link-to-psycho-education.nl."
        
        return [SlotSet("plan_week", plan)]

# Save weekly plan in calendar
class SavePlanWeekCalendar(Action):
    def name(self):
        return "action_save_plan_week_calendar"

    async def run(self, dispatcher, tracker, domain):
        
        success = True
        
        return [SlotSet("success_save_calendar_plan_week", success)]