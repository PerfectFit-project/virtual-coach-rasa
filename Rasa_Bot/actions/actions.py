# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
from typing import Any, Dict, Text

from paalgorithms import weekly_kilometers
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction

AGE = 30  # We should get this value from a database.


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
        # Calculates weekly kilometers based on age
        kilometers = weekly_kilometers(AGE)
        plan = "Sure, you should run %.1f kilometers this week. And please read through this " \
               "psycho-education: www.link-to-psycho-education.nl." % kilometers

        return [SlotSet("plan_week", plan)]


# Save weekly plan in calendar
class SavePlanWeekCalendar(Action):
    def name(self):
        return "action_save_plan_week_calendar"

    async def run(self, dispatcher, tracker, domain):

        success = True

        return [SlotSet("success_save_calendar_plan_week", success)]


# Validate input of liker scale form
class ValidateLikertForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_likert_form'

    def validate_likert_scale(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
    ) -> Dict[Text, Any]:
        """Validate likert_scale input."""

        try:
            likert_scale = int(value)
            if (likert_scale < 1) or (likert_scale > 5):
                dispatcher.utter_message("Kun je een geheel getal tussen 1 en 5 opgeven?")
                return {"likert_scale": None}
            else:

                # Create custom responses based on likert input
                if likert_scale >= 4:
                    dispatcher.utter_message("Fijn om te horen!")
                else:
                    dispatcher.utter_message("Jammer, probeer nu goed uit te rusten, "
                                             "dan gaat het de volgende keer vast beter!")
                # Save the input slot.
                return {"likert_scale": likert_scale}
        except ValueError:
            dispatcher.utter_message("Kun je een geheel getal tussen 1 en 5 opgeven?")
            return {"likert_scale": None}
