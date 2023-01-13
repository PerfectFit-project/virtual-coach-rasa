import datetime
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any
from virtual_coach_db.helper.definitions import VideoLinks
from . import validator
from .definitions import REDIS_URL
from .helper import get_latest_bot_utterance

celery = Celery(broker=REDIS_URL)


class SetSlotVideoLink(Action):
    """ this is an example for setting the slot of the video link"""
    def name(self):
        return "action_set_slot_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.TESTVIDEOLINK)]


class DisplayVideoLink(Action):
    """Display a certain video link"""

    def name(self):
        return "action_display_video_link"

    async def run(self, dispatcher, tracker, domain):
        link = tracker.get_slot('video_link')
        dispatcher.utter_message(text=link)
        return []


class DelayedMessage(Action):
    """Schedules a reminder"""

    def name(self):
        return "action_delayed_message_after_video"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        new_intent = 'EXTERNAL_done_with_video'
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, new_intent),
                         eta=datetime.datetime.now() + datetime.timedelta(seconds=30))
        return []


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

        video_clear = validator.validate_number_in_range_response(1, 2, value)
        if video_clear is None:
            dispatcher.utter_message(response="utter_please_answer_1_2")

        return {"video_clear_option": video_clear}
