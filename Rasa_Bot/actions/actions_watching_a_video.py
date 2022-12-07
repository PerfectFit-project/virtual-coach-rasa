import datetime
from rasa_sdk.events import ReminderScheduled
from rasa_sdk import Action
from typing import Text


class DelayedMessage(Action):
    """Schedules a reminder"""

    def name(self):
        return "action_delayed_message_after_video"

    async def run(self, dispatcher, tracker, domain):

        date = datetime.datetime.now() + datetime.timedelta(seconds=30)

        reminder = ReminderScheduled(
            "EXTERNAL_done_with_video",
            trigger_date_time=date,
            name="my_reminder",
            kill_on_user_message=False,
        )

        #TODO remove once working
        dispatcher.utter_message("I will remind you in 30 seconds")

        return [reminder]

class ActionReactToReminder(Action):
    """Will ask user about the video after watching"""
    def name(self):
        return "action_thanks_for_watching"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_thanks_for_watching")
        return []