import logging

from celery import Celery
from niceday_client import NicedayClient
from rasa_sdk import Action
from rasa_sdk.events import FollowupAction, SlotSet
from .definitions import REDIS_URL, NICEDAY_API_ENDPOINT

celery = Celery(broker=REDIS_URL)


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
        logging.info(slot)

        celery.send_task('celery_tasks.intervention_component_completed', (user_id, slot))
        logging.info("no celery error")

        return []


class SendMetadata(Action):
    def name(self):
        return "action_send_metadata"

    async def run(self, dispatcher, tracker, domain):
        id_file = tracker.get_slot("uploaded_file_id")
        dispatcher.utter_message(
            json_message={"text": "image",
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

        response = client.upload_file(user_id, 'tst.png', filepath, file)
        file_id = response['id']
        logging.info(response)
        logging.info(file_id)

        return[SlotSet("uploaded_file_id", file_id)]


class SetFilePath(Action):
    def name(self):
        return "action_set_file_path"

    async def run(self, dispatcher, tracker, domain):

        # TODO: This is hardcoded for testing. Needs to be set according to the use case

        filepath = '/app/tst.PNG'

        return[SlotSet("upload_file_path", filepath)]
