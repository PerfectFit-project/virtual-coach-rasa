"""
Contains custom actions related to the weekly reflection dialogue
"""

import logging

from . import validator
from .definitions import DATABASE_URL, REDIS_URL
from .helper import (get_latest_bot_utterance, get_random_activities,
                     store_dialog_closed_answer_to_db, store_dialog_open_answer_to_db,
                     store_dialog_closed_answer_list_to_db, store_user_intervention_state)
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.helper.definitions import (ExecutionInterventionComponents,
                                                 DialogQuestionsEnum, Phases)
from virtual_coach_db.helper.helper_functions import get_db_session
from virtual_coach_db.dbschema.models import InterventionActivity

celery = Celery(broker=REDIS_URL)


# Trigger relapse phase through celery
class TriggerWeeklyReflectionDialog(Action):
    def name(self):
        return "action_trigger_weekly_reflection"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        celery.send_task('celery_tasks.weekly_reflection_dialog',
                         (user_id, ExecutionInterventionComponents.WEEKLY_REFLECTION))

        return []


class ValidateHowWentNonSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_how_went_non_smoke_form'

    def validate_how_went_non_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate ehbo, me or self input"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_went_non_smoke':
            return {"how_went_non_smoke": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"how_went_non_smoke": None}

        return {"how_went_non_smoke": value}

