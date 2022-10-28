from virtual_coach_db.helper import ExecutionInterventionComponents

from .helper import get_latest_bot_utterance
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import Text, Dict, Any
from random import randint, seed


class GeneralActivityCheckRating(Action):
    """Check if the activity rating is in top five or not"""

    def name(self):
        return "general_activity_check_rating"

    async def run(self, dispatcher, tracker, domain):

        # at the moment we see only if it's higher
        # or lower then 5
        # TODO: check old scoring and determine if it's in top 5

        rating_value = tracker.get_slot('activity_useful_rating')

        if int(rating_value) <= 5:
            return [SlotSet("general_activity_low_high_rating", 'low')]
        else:
            return [SlotSet("general_activity_low_high_rating", 'high')]


class GetActivityUserInput(Action):
    """Check if the activity has been already done by the user"""

    def name(self):
        return "get_activity_user_input"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, uses a random name
        # TODO: get the name of the activity chosen from DB

        return [SlotSet("activity_user_input", "This is a random input")]


class CheckUserInputRequired(Action):
    """Check if the activity requires the input of the user"""

    def name(self):
        return "check_user_input_required"

    async def run(self, dispatcher, tracker, domain):

        # for testing purposes, activities 6 and 7 will require input
        # activities 8, 9, 10 will not require input
        # TODO: implement input needed logic

        rating_value = tracker.get_slot('activity_useful_rating')

        if int(rating_value) <= 7:
            return [SlotSet("is_user_input_required", True)]
        else:
            return [SlotSet("is_user_input_required", False)]


class CheckActivityDone(Action):
    """Check if the activity has been already done by the user"""

    def name(self):
        return "check_activity_done"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, returns false
        # TODO: implement logic

        return [SlotSet("is_activity_done", True)]


class ValidateActivityUsefulnessForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_activity_usefulness_form'

    def validate_activity_useful_rating(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate activity_useful_rating input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_activity_useful_rating':
            return {"activity_useful_rating": None}

        if not self._validate_activity_useful_rating_response(value):
            dispatcher.utter_message(response="utter_please_answer_1_to_10")
            return {"activity_useful_rating": None}

        return {"activity_useful_rating": value}

    @staticmethod
    def _validate_activity_useful_rating_response(value):
        if 1 <= int(value) <= 10:
            return True
        return False


class ValidateSaveOrEditForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_save_or_edit_form'

    def validate_save_or_edit_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate save_or_edit_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_save_or_edit_slot':
            return {"save_or_edit_slot": None}

        if not self._validate_save_or_edit_response(value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"save_or_edit_slot": None}

        return {"save_or_edit_slot": value}

    @staticmethod
    def _validate_save_or_edit_response(value):
        if value == '1' or value == '2':
            return True
        return False


class ValidateGeneralActivityDescriptionForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_general_activity_description_form'

    def validate_general_activity_description_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_description_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_general_activity_description_slot':
            return {"general_activity_description_slot": None}

        if not self._validate_response_length(value):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"general_activity_description_slot": None}

        return {"general_activity_description_slot": value}

    @staticmethod
    def _validate_response_length(value):
        if len(value) >= 50:
            return True
        return False


class SaveDescriptionInDb(Action):
    def name(self) -> Text:
        return 'save_description_in_db'

    async def run(self, dispatcher, tracker, domain):
        # pylint: disable=unused-argument
        """Save the provided description inf the DB."""
        description = tracker.get_slot('general_activity_description_slot')

        return []


class GetThreeRandomActivities(Action):
    def name(self) -> Text:
        return 'get_three_random_activities'

    async def run(self, dispatcher, tracker, domain):
        # pylint: disable=unused-argument
        """pick three random activities and sets the slots"""
        # TODO: implement resource getting and random assignment
        seed(1)
        value1 = randint(0, 10)
        value2 = randint(0, 10)
        value3 = randint(0, 10)
        activity_one = "activity " + str(value1)
        activity_two = "activity " + str(value2)
        activity_three = "activity " + str(value3)

        return [SlotSet("activity1_name", activity_one),
                SlotSet("activity2_name", activity_two),
                SlotSet("activity3_name", activity_three)]


class ValidateGeneralActivityNextActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_general_activity_next_activity_form'

    def validate_general_activity_next_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_next_activity_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_general_activity_next_activity_slot':
            return {"general_activity_next_activity_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"general_activity_next_activity_slot": None}

        if value == '4':
            seed(1)
            value1 = randint(0, 10)
            value2 = randint(0, 10)
            value3 = randint(0, 10)
            activity_one = "activity " + str(value1)
            activity_two = "activity " + str(value2)
            activity_three = "activity " + str(value3)

            SlotSet("activity1_name", activity_one)
            SlotSet("activity2_name", activity_two)
            SlotSet("activity3_name", activity_three)
            return {"general_activity_next_activity_slot": None}

        return {"general_activity_next_activity_slot": value}

    @staticmethod
    def _validate_response_value(value):
        if 1 <= int(value) <= 4:
            return True
        return False


class GetLastPerformedActivity(Action):
    """Get the last performed activity"""

    def name(self):
        return "get_last_performed_activity"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, returns a random name
        # TODO: implement logic

        return [SlotSet("last_activity_slot", "this is your last activity")]


class StoreActivityToFak(Action):
    """Check if the activity has been already done by the user"""

    def name(self):
        return "store_activity_to_fak"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, returns false
        # TODO: implement logic

        return []


class GetActivityCoachChoice(Action):
    """The coach chooses the next activity and saves it in the slot"""

    def name(self):
        return "get_activity_coach_choice"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, returns false
        # TODO: implement logic

        return [SlotSet("chosen_activity_slot", "this is the chosen activity")]


class CheckWhoDecides(Action):
    """TCheck if the user or the coach decides the next activity"""

    def name(self):
        return "check_who_decides"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, the user decides
        # TODO: implement logic

        decider = 'user'

        return [SlotSet("who_decides_slot", decider)]


class SetSlotGeneralActivity(Action):
    def name(self):
        return "action_set_slot_general_activity"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.GENERAL_ACTIVITY)]

