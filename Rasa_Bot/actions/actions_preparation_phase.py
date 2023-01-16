from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import PreviousDialog
from celery import Celery
from .definitions import REDIS_URL

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
        expectedTimeInterval = tracker.get_slot('expected_next_time_interval')
        message = "Ik verwacht dat het volgende onderdeel " + expectedTimeInterval[0] + " tot " \
                  + expectedTimeInterval[1] + " minuten zal duren."
        dispatcher.utter_message(text=message)
        return []
