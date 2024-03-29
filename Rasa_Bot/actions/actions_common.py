import logging
import os

from celery import Celery
from niceday_client import NicedayClient
from rasa_sdk import Action
from rasa_sdk.events import FollowupAction, SlotSet

from .definitions import REDIS_URL, NICEDAY_API_ENDPOINT, TRIGGER_INTENT
from .helper import mark_completion

from virtual_coach_db.helper.definitions import ComponentsTriggers

celery = Celery(broker=REDIS_URL)


class ActionLaunchReschedulingPrep(Action):
    """Trigger the preparation dialog rescheduling"""

    def name(self):
        return "action_launch_rescheduling_prep"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        new_intent = ComponentsTriggers.RESCHEDULING_PREPARATION

        celery.send_task(TRIGGER_INTENT,
                         (user_id, new_intent))
        return []


class ActionEndDialog(Action):
    """Action to cleanly terminate the dialog."""
    # ATM this action just call the default restart action
    # but this can be used to perform actions that might be needed
    # at the end of each dialog
    def name(self):
        return "action_end_dialog"

    async def run(self, dispatcher, tracker, domain):

        return [FollowupAction('action_restart')]


# Store last intervention component in database
class MarkDialogAsCompleted(Action):
    def name(self):
        return "mark_dialog_as_completed"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        slot = tracker.get_slot("current_intervention_component")
        mark_completion(user_id, slot)

        return []


class SendMetadata(Action):
    def name(self):
        return "action_send_metadata"

    async def run(self, dispatcher, tracker, domain):
        """
        Sends the text message specified in the 'text' value of the json_message,
        and sends the image identified by the id_file under the 'attachmentIds' key.

        The id_file is obtained in the action_upload_file as a result of
        a file uploaded to the NiceDay server. The id is stored in the
        uploaded_file_id slot.

        The uploaded file is a local one, and is uses the file indicated
        by the action_set_file_path
        """
        id_file = tracker.get_slot("uploaded_file_id")
        dispatcher.utter_message(
            json_message={"text": "Klik op het plaatje",
                          "attachmentIds": [id_file]},
        )
        return[]


class UploadFile(Action):
    def name(self):
        return "action_upload_file"

    async def run(self, dispatcher, tracker, domain):
        client = NicedayClient(NICEDAY_API_ENDPOINT)
        user_id = int(tracker.current_state()['sender_id'])

        filepath = tracker.get_slot('upload_file_path')
        with open(filepath, 'rb') as content:
            file = content.read()

        response = client.upload_file(user_id, filepath, file)
        file_id = response['id']
        logging.info(response)

        return[SlotSet("uploaded_file_id", file_id)]

class DeleteFile(Action):
    def name(self):
        return "action_delete_file"

    async def run(self, dispatcher, tracker, domain):
        file_path = tracker.get_slot("upload_file_path")

        try:
            os.remove(file_path)
        except FileNotFoundError:
            logging.info("File to remove not found.")

        return[]


class SetFilePath(Action):
    def name(self):
        return "action_set_file_path"

    async def run(self, dispatcher, tracker, domain):

        # TODO: This is hardcoded for testing. Needs to be set according to the use case

        filepath = '/app/chart.PNG'

        return[SlotSet("upload_file_path", filepath)]
