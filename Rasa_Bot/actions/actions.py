# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
import datetime
from typing import Any, Dict, Text

from paalgorithms import weekly_kilometers
from rasa_sdk import Action
from rasa_sdk.events import ReminderScheduled, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction


AGE = 30  # TODO_db: We should get this value from a database.


# Get the user's name from the database.
# Save the extracted name to a slot.
class GetNameFromDatabase(Action):
    def name(self):
        return "action_get_name_from_database"

    async def run(self, dispatcher, tracker, domain):

        name = "Kees"  # TODO_db

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
class ValidatePaEvaluationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_evaluation_form'

    def validate_pa_evaluation_form(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
    ) -> Dict[Text, Any]:
        """Validate pa_response_likert input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message("Kun je een geheel getal tussen 1 en 5 opgeven?")
            return {"pa_evaluation_response": None}
        else:
            pa_response_likert = int(value)
            # Create custom responses based on likert input
            if pa_response_likert >= 4:
                dispatcher.utter_message("Fijn om te horen!")
            else:
                dispatcher.utter_message("Jammer, probeer nu goed uit te rusten, "
                                         "dan gaat het de volgende keer vast beter!")
            # Save the input slot.
            return {"pa_evaluation_response": pa_response_likert}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 5):
            return False
        return True


# Set reminder, triggered by external scheduler
class ActionSetReminder(Action):
    """To schedule a reminder"""

    def name(self):
        return "action_set_reminder"

    async def run(self, dispatcher, tracker, domain):

        date0 = datetime.datetime.now()

        # used only for development (use the daily reminder below for production)
        t = 2
        dispatcher.utter_message(f"I will remind you in {t} seconds.")
        date = date0 + datetime.timedelta(seconds=t)

        # the daily reminder
        # TODO_db: get user's time setting from database.
        # Here using a fixed time 9:00AM.
        # dispatcher.utter_message("I will remind you 9:00AM every day.")
        # reminder_hour = 9
        # date = datetime.datetime(date0.year, date0.month, date0.day,
        #                         reminder_hour, 0, 0, 0)
        # if (date0.hour > reminder_hour):
        #     date = date + datetime.timedelta(days=1)

        reminder = ReminderScheduled(
            "EXTERNAL_utter_reminder",
            trigger_date_time=date,
            entities="",
            name="Daily Reminder",
            kill_on_user_message=False,
        )

        return [reminder]
