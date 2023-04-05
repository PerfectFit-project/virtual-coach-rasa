import datetime
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any
from virtual_coach_db.helper.definitions import VideoLinks, Components, ComponentsTriggers
from . import validator
from .definitions import REDIS_URL
from .helper import get_latest_bot_utterance

celery = Celery(broker=REDIS_URL)


class ActionLaunchWatchVideoDialog(Action):
    """Trigger the watch a video dialog"""

    def name(self):
        return "action_launch_watch_video_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        new_intent = ComponentsTriggers.WATCH_VIDEO
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, new_intent))
        return []


class ActionLaunchReschedulingPrep(Action):
    """Trigger the preparation dialogs rescheduling"""

    def name(self):
        return "action_launch_rescheduling_prep"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        new_intent = ComponentsTriggers.RESCHEDULING_PREPARATION

        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, new_intent))
        return []


class SetMedicationVideoLink(Action):
    """ set the link to the medication video"""
    def name(self):
        return "action_set_medication_video_link"

    async def run(self, dispatcher, tracker, domain):

        return [SlotSet("video_link",
                        VideoLinks.MEDICATION_VIDEO)]


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
        if video_clear is False:
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"video_clear_option": None}

        return {"video_clear_option": value}


class ContinueAfterVideo(Action):
    def name(self):
        return "action_continue_after_video"

    async def run(self, dispatcher, tracker, domain):
        # checks in which dialog the user is, and resumes the correct flow accordingly
        current_dialog = tracker.get_slot('current_intervention_component')

        if current_dialog == Components.RELAPSE_DIALOG_RELAPSE:
            # resumes the relapse dialog opening the ehbo_me_self_lapse_form.
            # The flow will then depend on the chosen option in the form
            return [FollowupAction('ehbo_me_self_lapse_form')]
