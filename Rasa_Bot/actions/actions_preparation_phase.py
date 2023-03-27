from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any
from virtual_coach_db.helper.definitions import (Components,
                                                 ComponentsTriggers,
                                                 DialogExpectedDuration)

from . import validator
from .definitions import MORNING, AFTERNOON, REDIS_URL, TIMEZONE
from .helper import get_latest_bot_utterance
from .actions_rescheduling_dialog import get_reschedule_date

import datetime


celery = Celery(broker=REDIS_URL)

class ExpectedTimeNextPart(Action):
    """Give expected time of next part"""

    def name(self):
        return "action_expected_time_next_part"

    async def run(self, dispatcher, tracker, domain):
        nextDialog = str(tracker.get_slot('current_intervention_component'))
        expectedTimeInterval = DialogExpectedDuration[nextDialog].split(" ")
        message = "Ik verwacht dat het volgende onderdeel " + expectedTimeInterval[0] + " tot " \
                  + expectedTimeInterval[1] + " minuten zal duren.⏱️"
        dispatcher.utter_message(text=message)
        return []


class ValidateNowOrLaterForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_next_part_now_or_later_form"

    def validate_now_or_later(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """validate next part now or later form"""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_now_or_later':
            return {"now_or_later": None}

        now_or_later = validator.validate_number_in_range_response(1, 2, value)
        if not now_or_later:
            dispatcher.utter_message(response="utter_please_answer_1_2")

        return {"now_or_later": value}

class ValidatePickADaypartForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_pick_a_daypart_form"

    def validate_chosen_daypart(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """validate pick a daypart form"""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_chosen_daypart':
            return {"chosen_daypart": None}

        correct_format = validator.validate_number_in_range_response(1, 4, value)
        if not correct_format:
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")

        return {"chosen_daypart": value}

class StartNextDialog(Action):
    """set trigger for next dialog"""

    def name(self) -> Text:
        return "action_start_next_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        current_dialog = tracker.get_slot('current_intervention_component')

        # if the dialog is the profile creation, launch that
        if current_dialog == Components.PROFILE_CREATION:
            return [FollowupAction('utter_profile_creation_start_1')]

        # if the dialog is a video one, launch the watch a video dialog
        celery.send_task('celery_tasks.trigger_intervention_component',
                         (user_id,
                          ComponentsTriggers.WATCH_VIDEO))


class Schedule_Next_Prep_Phase(Action):
    """ reschedule the dialog for another time """
    def name(self) -> Text:
        return "action_schedule_next_preparation_phase"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        chosen_option = int(tracker.get_slot('chosen_daypart'))
        timestamp = tracker.get_slot('daypart_options_timestamp')
        dialog = tracker.get_slot('current_intervention_component')
        eta = get_reschedule_date(timestamp, chosen_option)

        celery.send_task('celery_tasks.reschedule_dialog', (user_id, dialog, eta))

def get_daypart_options_str() -> list:
    options = []

    current_time = datetime.datetime.now().astimezone(TIMEZONE)

    # In the morning
    if MORNING[0] <= current_time.hour < MORNING[1]:
        options += ["Vanmiddag",
                    "Vanavond",
                    "Morgenochtend"]

    # In the afternoon
    elif AFTERNOON[0] <= current_time.hour < AFTERNOON[1]:
        options += ["Vanavond",
                    "Morgenochtend",
                    "Morgenmiddag"]

    # In the evening or night
    else:
        options += ["Morgenochtend",
                    "Morgenmiddag",
                    "Morgenavond"]

    return options


class AskNewTime(Action):
    def name(self) -> Text:
        return "action_ask_new_time"

    async def run(self, dispatcher, tracker, domain):
        options = get_daypart_options_str()

        prompt = "Wanneer zou je het volgende onderdeel willen doen? Typ '1' als je het volgende"\
                 "onderdeel over 1 uur wilt doen. Typ '2' als je het {0} wilt doen. Typ '3'"\
                 " als je het {1} wilt doen. En typ '4' als " \
                 "je het {2} wilt doen. "
        utterance = prompt.format(*options)

        timestamp = datetime.datetime.timestamp(datetime.datetime.now())
        return [SlotSet("daypart_options_timestamp", timestamp),
                SlotSet("daypart_options_string", utterance)]
