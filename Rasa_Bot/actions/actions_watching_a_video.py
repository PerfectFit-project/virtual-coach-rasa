import datetime
from rasa_sdk.events import ReminderScheduled
from rasa_sdk import Action, Tracker
from typing import Text, Dict, Any
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from .helper import get_latest_bot_utterance


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


class ValidateVideoClearForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_video_clear_form'

    def validate_video_clear(
            self, value: Text, dispatcher: CollectingDispatcher) -> Dict[Text, Any]:
        """Validate video clear input."""

        if value == 1:
            dispatcher.utter_message(response="utter_clear_confirmation")
            dispatcher.utter_message(response="utter_finish_video_dialog")
        if value == 2:
            dispatcher.utter_message(response="utter_video_link")
        else:
            dispatcher.utter_message(response="utter_please_answer_video_clear")

        return {}
