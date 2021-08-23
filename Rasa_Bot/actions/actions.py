# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
import datetime
from typing import Any, Text, Dict, List

from paalgorithms import weekly_kilometers
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, ReminderScheduled, ReminderCancelled
from rasa_sdk.executor import CollectingDispatcher


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


# Set auto reminder, triggered by external scheduler
class ActionSetReminder(Action):
    """To schedule a reminder"""

    def name(self) -> Text:
        return "action_set_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # TODO: read user's time setting
        date0 = datetime.datetime.now()
        # reminder_hour = 9
        # date = datetime.datetime(
        #     date0.year,
        #     date0.month,
        #     date0.day,
        #     reminder_hour,
        #     0,
        #     0,
        #     0)
        # if (date0.hour > reminder_hour):
        #     date = date + datetime.timedelta(days=1)
        date = date0 + datetime.timedelta(seconds=3)

        reminder = ReminderScheduled(
            "EXTERNAL_send_reminder",
            trigger_date_time=date,
            entities="",
            name="Daily Reminder",
            kill_on_user_message=False,
        )

        return [reminder]


class ActionReactToReminder(Action):
    """Reach out to user to remind the high risk situations."""

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            f"Do you foresee any high risk situations for smoking today?")

        return []
