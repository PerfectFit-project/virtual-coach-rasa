from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.dbschema.models import FirstAidKit
from virtual_coach_db.helper.helper import get_db_session

from Rasa_Bot.actions.definitions import DATABASE_URL


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

        if selected is not None:

            kit_exists = True

            for activity_idx, activity in enumerate(selected):
                kit_text += str(activity_idx + 1) + ") "
                if activity.intervention_activity_id is None:
                    kit_text += activity.user_activity_title
                else:
                    kit_text += activity.intervention_activity.intervention_activity_title
                if not activity_idx == len(selected) - 1:
                    kit_text += "\n"

        return [SlotSet("first_aid_kit_text", kit_text),
                SlotSet("first_aid_kit_exists", kit_exists)]