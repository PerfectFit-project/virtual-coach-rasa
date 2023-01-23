from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import PreviousDialog
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Text, Dict, Any
from celery import Celery
from . import validator
from .definitions import REDIS_URL, MORNING, AFTERNOON, EVENING, TIMEZONE
from .helper import get_latest_bot_utterance
import datetime

celery = Celery(broker=REDIS_URL)


class SetSlotPreviousDialog(Action):
    """ this is an example for setting the slot of the previous dialog"""

    def name(self):
        return "action_set_slot_previous_dialog"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("expected_next_time_interval",
                        PreviousDialog.DIALOG1)]


class ExpectedTimeNextPart(Action):
    """Give expected time of next part"""

    def name(self):
        return "action_expected_time_next_part"

    async def run(self, dispatcher, tracker, domain):
        expectedTimeInterval = tracker.get_slot('expected_next_time_interval').split(" ")
        message = "Ik verwacht dat het volgende onderdeel " + expectedTimeInterval[0] + " tot " \
                  + expectedTimeInterval[1] + " minuten zal duren.⏱️"
        dispatcher.utter_message(text=message)
        return []


class ValidateNowOrLaterFrom(FormValidationAction):
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
        if now_or_later is None:
            dispatcher.utter_message(response="utter_please_answer_1_2")

        return {"now_or_later": now_or_later}


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

        prompt = "Wanneer zou je het volgende onderdeel willen doen? Typ '1' als je het volgende onderdeel over 1 " \
                 "uur wilt doen. Typ '2' als je het {0} wilt doen. Typ '3' als je het {1} wilt doen. En typ '4' als " \
                 "je het {2} wilt doen. "
        utterance = prompt.format(*options)
        dispatcher.utter_message(text=utterance)

        timestamp = datetime.datetime.timestamp(datetime.datetime.now())
        #return [SlotSet("daypart_options_timestamp", timestamp)]
        return []
