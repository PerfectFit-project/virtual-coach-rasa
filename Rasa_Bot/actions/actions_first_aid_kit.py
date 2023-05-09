import logging

from . import validator
from .definitions import DATABASE_URL, REDIS_URL
from .helper import (get_latest_bot_utterance,
                     get_user_intervention_activity_inputs,
                     get_faik_text)

from celery import Celery
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.dbschema.models import InterventionActivity
from virtual_coach_db.helper.helper_functions import get_db_session


celery = Celery(broker=REDIS_URL)


class ActionStartFak(Action):
    """Action to run the First Aid Kit from external trigger"""

    def name(self):
        return "action_start_fak"

    async def run(self, dispatcher, tracker, domain):

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        logging.info("Launching first aid kit celery intent")
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

        if current_intervention == 'NONE':
            return[FollowupAction('action_end_dialog')]

        new_intent = 'EXTERNAL_' + current_intervention
        logging.info(new_intent)
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id, new_intent),
                         eta=datetime.now() + timedelta(seconds=10))

        return []


class ActionGetFirstAidKit(Action):
    """To get the first aid kit from the database."""

    def name(self):
        return "action_get_first_aid_kit"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        kit_text, filled, activity_ids_list = get_faik_text(user_id)

        return [SlotSet('first_aid_kit_text', kit_text),
                SlotSet('first_aid_kit_filled', filled),
                SlotSet('first_aid_kit_activities_ids', activity_ids_list)]


class ValidateFirstAidKitChosenActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_first_aid_kit_chosen_activity_form'

    def validate_first_aid_kit_chosen_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate first_aid_kit_chosen_activity_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_first_aid_kit_chosen_activity_slot':
            return {"first_aid_kit_chosen_activity_slot": None}

        if not validator.validate_number_in_range_response(n_min=1, n_max=5, 
                                                           response=value):
            return {"first_aid_kit_chosen_activity_slot": None}

        activity_ids_list = tracker.get_slot('first_aid_kit_activities_ids')

        return {"first_aid_kit_chosen_activity_slot": activity_ids_list[int(value) - 1]}


class ActionFirstAidKitCheckUserInputRequired(Action):
    """Check whether chosen activity requires user input."""

    def name(self):
        return "action_first_aid_kit_check_user_input_required"

    async def run(self, dispatcher, tracker, domain):
        
        # Get ID of chosen activity
        activity_id = tracker.get_slot('first_aid_kit_chosen_activity_slot')

        # Check in database if activity requires user input
        session = get_db_session(db_url=DATABASE_URL)
        selected = (
            session.query(
                InterventionActivity
                )
            .filter_by(
                intervention_activity_id=activity_id
                ).one()
            )

        input_required = int(selected.user_input_required)

        return [SlotSet('first_aid_kit_chosen_activity_input_required', 
                        input_required)]
    

class ActionFirstAidKitGetUserInput(Action):
    """Get most recent user input for chosen activity from database."""

    def name(self):
        return "action_first_aid_kit_get_user_input"

    async def run(self, dispatcher, tracker, domain):
        
        # Get ID of chosen activity
        activity_id = tracker.get_slot('first_aid_kit_chosen_activity_slot')

        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, 
                                                            activity_id)
        last_input = user_inputs[-1].user_input

        return [SlotSet("first_aid_kit_user_input_slot", last_input)]


class ActionFirstAidKitGetInstructions(Action):
    """Get instructions for chosen activity from database."""

    def name(self):
        return "action_first_aid_kit_get_instructions"

    async def run(self, dispatcher, tracker, domain):
        
        # Get ID of chosen activity
        activity_id = tracker.get_slot('first_aid_kit_chosen_activity_slot')

        session = get_db_session(db_url=DATABASE_URL)
        selected = (
            session.query(
                InterventionActivity
                )
            .filter_by(
                intervention_activity_id=activity_id
                ).one()
            )

        instructions = selected.intervention_activity_full_instructions

        return [SlotSet("first_aid_kit_instructions_slot", instructions)]


class ValidateFirstAidKitEndForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_first_aid_kit_end_form'

    def validate_first_aid_kit_end_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate first_aid_kit_end_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_first_aid_kit_end_slot':
            return {"first_aid_kit_end_slot": None}

        if not validator.validate_number_in_range_response(n_min=1, n_max=2, 
                                                           response=value):
            return {"first_aid_kit_end_slot": None}

        return {"first_aid_kit_end_slot": int(value)}


class ActionFirstAidKitRepeat(Action):
    """Repeat first aid kit dialog."""

    def name(self):
        return "action_first_aid_kit_repeat"

    async def run(self, dispatcher, tracker, domain):
        
        return [FollowupAction('utter_first_aid_kit_show_activity_titles_1')]
