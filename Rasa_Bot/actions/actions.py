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
from paalgorithms import weekly_kilometers
    
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
        age = 30 # We should get this value from a database.
        WeeklyKilometers = weekly_kilometers(age) # Calculates weekly kilometers based on age
        plan = "Sure, you should run %.1f kilometers this week. And please read through this psycho-education: www.link-to-psycho-education.nl." %WeeklyKilometers
        
        return [SlotSet("plan_week", plan)]

# Save weekly plan in calendar
class SavePlanWeekCalendar(Action):
    def name(self):
        return "action_save_plan_week_calendar"

    async def run(self, dispatcher, tracker, domain):
        
        success = True
        
        return [SlotSet("success_save_calendar_plan_week", success)]