from celery import Celery
from rasa_sdk import Action
from virtual_coach_db.helper.definitions import Components
from .definitions import REDIS_URL

celery = Celery(broker=REDIS_URL)


class ActionTriggerRelapseDialog(Action):
    """Trigger the relapse the dialog"""

    def name(self):
        return "action_trigger_relapse_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.RELAPSE_DIALOG))


class ActionTriggerFirstAidDialog(Action):
    """Trigger the first aid dialog"""

    def name(self):
        return "action_trigger_first_aid_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.FIRST_AID_KIT))


class ActionTriggerExplainFirstAidVideoDialog(Action):
    """Trigger the first aid dialog explanation video"""

    def name(self):
        return "action_trigger_explanation_first_aid_video_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id,
                                                              Components.FIRST_AID_KIT_VIDEO))


class ActionTriggerGeneralActivityDialog(Action):
    """Trigger the general activity dialog"""

    def name(self):
        return "action_trigger_general_activity_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.GENERAL_ACTIVITY))


class ActionTriggerMedicineVideoDialog(Action):
    """Trigger the medicine video"""

    def name(self):
        return "action_trigger_video_medicine_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.MEDICATION_TALK))


class ActionTriggerUncompletedDialog(Action):
    """Trigger uncompleted dialog if there is one"""

    def name(self):
        return "action_trigger_uncompleted_dialog"

    async def run(self, dispatcher, tracker, domain):
        
        user_id = tracker.current_state()['sender_id']
        
        # TODO: let state machine figure out whether there is a
        # valid uncompleted dialog to run and start it if there is one.
        # If there is no uncompleted dialog, the external trigger
        # EXTERNAL_no_valid_uncompleted_dialog should be triggered
        # by the state machine

        celery.send_task('celery_tasks.user_trigger_dialog', 
                         (user_id, Components.CONTINUE_UNCOMPLETED_DIALOG))
