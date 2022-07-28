import logging

from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import FollowupAction
from .definitions import REDIS_URL


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
