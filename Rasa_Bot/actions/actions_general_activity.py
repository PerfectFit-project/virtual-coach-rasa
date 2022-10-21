from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import Text, Dict, Any


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
        # TODO: get the name of the activity cheosen from DB

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


class ValidateSaveOrEditForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_save_or_edit_form'

    def validate_save_or_edit_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate save_or_edit_slot input."""
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
        """Validate save_or_edit_slot input."""
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

        activity_one = "activity 1"
        activity_two = "activity 1"
        activity_three = "activity 1"

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
        if not self._validate_response_length(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"general_activity_next_activity_slot": None}

        return {"general_activity_next_activity_slot": value}

    @staticmethod
    def _validate_response_length(value):
        if int(value) >= 1 or int(value) <= 4:
            return True
        return False
