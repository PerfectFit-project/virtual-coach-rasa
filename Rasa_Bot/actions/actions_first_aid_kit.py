from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.dbschema.models import FirstAidKit
from virtual_coach_db.helper.helper_functions import get_db_session

from .definitions import DATABASE_URL, NUM_TOP_ACTIVITIES, REDIS_URL

celery = Celery(broker=REDIS_URL)


class ActionStartFak(Action):
    """Action to run the First Aid Kit from external trigger"""

    def name(self):
        return "action_start_fak"

    async def run(self, dispatcher, tracker, domain):

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, 'CENTRAL_get_first_aid_kit'))

        return []


class ActionResumeAfterFak(Action):
    """Action to run the First Aid Kit from external trigger"""

    def name(self):
        return "action_resume_after_fak"

    async def run(self, dispatcher, tracker, domain):

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        current_intervention = tracker.get_slot('current_intervention_component')
        new_intent = 'EXTERNAL_' + current_intervention
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, new_intent))

        return []


class ActionGetFirstAidKit(Action):
    """To get the first aid kit from the database."""

    def name(self):
        return "action_get_first_aid_kit"

    async def run(self, dispatcher, tracker, domain):

        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()['sender_id']

        selected = (
            session.query(
                FirstAidKit
            )
            .filter(
                FirstAidKit.users_nicedayuid == user_id
            )
            .all()
        )

        kit_text = ""
        kit_exists = False

        # the kit exists
        if selected is not None:

            kit_exists = True

            # get up to the highest rated activities
            sorted_activities = sorted(
                selected,
                key=lambda x: x.activity_rating
                )[:NUM_TOP_ACTIVITIES]

            for activity_idx, activity in enumerate(sorted_activities):
                kit_text += str(activity_idx + 1) + ") "
                if activity.intervention_activity_id is None:
                    kit_text += activity.user_activity_title
                else:
                    kit_text += activity.intervention_activity.intervention_activity_title
                if not activity_idx == len(selected) - 1:
                    kit_text += "\n"

            dispatcher.utter_message(template="utter_first_aid_kit",
                                     first_aid_kit_text=kit_text)
        # the kit doesn't exist
        else:
            dispatcher.utter_message(template="utter_first_aid_kit_empty")

        return []


class ActionSetContinuation(Action):
    """Set the dialog_to_continue slot"""

    def name(self):
        return "action_set_continuation"

    async def run(self, dispatcher, tracker, domain):
        current_intervention = tracker.get_slot('current_intervention_component')

        return [SlotSet("dialog_to_continue", current_intervention)]
