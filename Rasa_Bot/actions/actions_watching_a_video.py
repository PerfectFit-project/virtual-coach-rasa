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

        date = datetime.datetime.now() + datetime.timedelta(seconds=2)

        reminder = ReminderScheduled(
            "EXTERNAL_done_with_video",
            trigger_date_time=date,
            name="my_reminder",
            kill_on_user_message=False,
        )

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

    def validate_video_clear_option(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate video clear input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_video_clear_option':
            return {"video_clear_option": None}

        video_clear = self._validate_video_clear_response(value)
        if video_clear is None:
            dispatcher.utter_message(response="utter_please_answer_1_2")

        return {"video_clear_option": video_clear}

    @staticmethod
    def _validate_video_clear_response(value):
        if value == "1":
            return True
        if value == "2":
            return False
        return None
