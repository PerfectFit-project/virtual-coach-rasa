# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
import datetime
from typing import Any, Dict, Text

from paalgorithms import weekly_kilometers
from rasa_sdk import Action, Tracker
from rasa_sdk.events import ReminderScheduled, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
#from virtual_coach_db.dbschema.models import Users
#from virtual_coach_db.helper.helper import get_db_session

AGE = 30  # TODO_db: We should get this value from a database.


# Get the sender_id for the current user, i.e. the user ID
class GetSenderIDFromTracker(Action):
    def name(self):
        return "action_get_sender_id_from_tracker"

    async def run(self, dispatcher, tracker, domain):

        sender_id = tracker.current_state()['sender_id']
        dispatcher.utter_message("The ID is {sender_id}.")

        return [SlotSet("sender_id", sender_id)]


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

    def validate_pa_evaluation_response(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_evaluation_response input."""

        if not self._is_valid_input(value):
            return {"pa_evaluation_response": None}
        pa_evaluation_response = int(value)
        return {"pa_evaluation_response": pa_evaluation_response}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 5):
            return False
        return True


# Have a custom response based on the pa_evaluation response
class ActionPaEvaluationFormFilled(Action):
    """Custom response based on PA evaluation form"""

    def name(self):
        return "action_pa_likert_form_filled"

    async def run(self, dispatcher, tracker, domain):
        pa_evaluation_response = tracker.get_slot("pa_evaluation_response")

        if pa_evaluation_response >= 4:
            dispatcher.utter_message("Fijn om te horen dat het goed ging!")
        else:
            dispatcher.utter_message("Jammer, probeer nu goed uit te rusten, "
                                     "dan gaat het de volgende keer vast beter!")
        return []


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
