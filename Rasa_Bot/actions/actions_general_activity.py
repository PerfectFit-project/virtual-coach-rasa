import secrets

from sqlalchemy import update
from virtual_coach_db.dbschema.models import (InterventionActivitiesPerformed,
                                              FirstAidKit,
                                              InterventionActivity)
from virtual_coach_db.helper import ExecutionInterventionComponents
from virtual_coach_db.helper.helper_functions import get_db_session
from .definitions import DATABASE_URL, NUM_TOP_ACTIVITIES
from .helper import get_latest_bot_utterance
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import Text, Dict, Any


class CheckIfFirstExecutionGA(Action):
    """Check if it is the first execution"""

    def name(self):
        return "check_if_first_execution_ga"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()["sender_id"]
        session = get_db_session(db_url=DATABASE_URL)

        performed_activity = (
            session.query(InterventionActivitiesPerformed)
            .filter(InterventionActivitiesPerformed.users_nicedayuid == user_id)
            .all()
        )

        # if the query result is empty, no activity has been performed yet
        first_execution = not bool(performed_activity)

        return [SlotSet("general_activity_first_execution", first_execution)]


class GeneralActivityCheckRating(Action):
    """Check if the activity rating is in top five or not"""

    def name(self):
        return "general_activity_check_rating"

    async def run(self, dispatcher, tracker, domain):

        rating_value = int(tracker.get_slot("activity_useful_rating"))
        activity_id = int(tracker.get_slot("last_activity_id_slot"))

        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()["sender_id"]

        # get the highest scored activities
        top_five_activities = (
            session.query(FirstAidKit)
            .order_by(FirstAidKit.activity_rating.desc())
            .filter(FirstAidKit.users_nicedayuid == user_id)
            .limit(NUM_TOP_ACTIVITIES)
            .all()
        )

        current_record = (
            session.query(FirstAidKit) .filter(
                FirstAidKit.users_nicedayuid == user_id,
                FirstAidKit.intervention_activity_id == activity_id) .all())

        # FIXME: what if the len of the top_five_activities is 0
        lowest_score = top_five_activities[-1].activity_rating

        # if the activity is not in the FAK, add it
        if not current_record:

            save_activity_to_fak(user_id, activity_id, rating_value)

            session.commit()

            return [SlotSet("general_activity_low_high_rating", "high")]

        # update the row containing the activity with the new rating
        session.execute(
            update(FirstAidKit) .where(
                FirstAidKit.first_aid_kit_id == current_record[0].first_aid_kit_id) .values(
                activity_rating=rating_value))

        session.commit()

        if rating_value > lowest_score:
            return [SlotSet("general_activity_low_high_rating", "high")]

        return [SlotSet("general_activity_low_high_rating", "low")]


class GetActivityUserInput(Action):
    """Get the user input and save it in the slot"""

    def name(self):
        return "get_activity_user_input"

    async def run(self, dispatcher, tracker, domain):

        activity_id = int(tracker.get_slot("last_activity_id_slot"))
        user_id = int(tracker.current_state()["sender_id"])

        user_inputs = get_user_intervention_activity_inputs(
            user_id, activity_id)
        last_input = user_inputs[-1].user_input

        return [SlotSet("activity_user_input", last_input)]


class CheckUserInputRequired(Action):
    """Check if the activity requires the input of the user"""

    def name(self):
        return "check_user_input_required"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot("last_activity_id_slot")
        session = get_db_session(db_url=DATABASE_URL)

        is_input_required = (
            session.query(InterventionActivity)
            .filter(InterventionActivity.intervention_activity_id == activity_id)
            .all()
        )

        return [SlotSet("is_user_input_required",
                        is_input_required[0].user_input_required)]


class CheckActivityDone(Action):
    """Check if an input for the activity has been
    already provided by the user"""

    def name(self):
        return "check_activity_done"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot("last_activity_id_slot")
        user_id = tracker.current_state()["sender_id"]

        user_inputs = get_user_intervention_activity_inputs(
            user_id, activity_id)

        # FIXME: could it happen the len of user_inputs is 0?
        if user_inputs[-1].user_input is None:
            activity_done = False
        else:
            activity_done = True

        return [SlotSet("is_activity_done", activity_done)]


class ValidateActivityUsefulnessForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_activity_usefulness_form"

    def validate_activity_useful_rating(self,
                                        value: Text,
                                        dispatcher: CollectingDispatcher,
                                        tracker: Tracker,
                                        domain: Dict[Text,
                                                     Any]) -> Dict[Text,
                                                                   Any]:
        # pylint: disable=unused-argument
        """Validate activity_useful_rating input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != "utter_ask_activity_useful_rating":
            return {"activity_useful_rating": None}

        if not self._validate_activity_useful_rating_response(value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"activity_useful_rating": None}

        return {"activity_useful_rating": value}

    @staticmethod
    def _validate_activity_useful_rating_response(value):
        if 0 <= int(value) <= 10:
            return True
        return False


class ValidateSaveOrEditForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_save_or_edit_form"

    def validate_save_or_edit_slot(self,
                                   value: Text,
                                   dispatcher: CollectingDispatcher,
                                   tracker: Tracker,
                                   domain: Dict[Text,
                                                Any]) -> Dict[Text,
                                                              Any]:
        # pylint: disable=unused-argument
        """Validate save_or_edit_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != "utter_ask_save_or_edit_slot":
            return {"save_or_edit_slot": None}

        if not self._validate_save_or_edit_response(value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"save_or_edit_slot": None}

        return {"save_or_edit_slot": value}

    @staticmethod
    def _validate_save_or_edit_response(value):
        if value in ("1", "2"):
            return True
        return False


class ValidateGeneralActivityDescriptionForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_general_activity_description_form"

    def validate_general_activity_description_slot(
        self, value: Text, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_description_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != "utter_ask_general_activity_description_slot":
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
        return "save_description_in_db"

    async def run(self, dispatcher, tracker, domain):
        """Save the provided description inf the DB."""

        description = tracker.get_slot("general_activity_description_slot")

        activity_id = tracker.get_slot("last_activity_id_slot")
        user_id = tracker.current_state()["sender_id"]

        user_inputs = get_user_intervention_activity_inputs(
            user_id, activity_id)
        row_id = user_inputs[-1].intervention_activities_performed_id

        session = get_db_session(db_url=DATABASE_URL)

        session.execute(
            update(InterventionActivitiesPerformed).where(
                InterventionActivitiesPerformed.intervention_activities_performed_id == row_id)
            .values(
                user_input=description))

        session.commit()

        return []


class GetThreeRandomActivities(Action):
    def name(self) -> Text:
        return "get_three_random_activities"

    async def run(self, dispatcher, tracker, domain):
        """pick three random activities and sets the slots"""

        activity_id = tracker.get_slot("last_activity_id_slot")

        rnd_activities = get_random_activities(activity_id, 3)
        rnd_activities_ids = [
            activity.intervention_activity_id for activity in rnd_activities]

        return [
            SlotSet("activity1_name",
                    rnd_activities[0].intervention_activity_title),
            SlotSet("activity2_name",
                    rnd_activities[1].intervention_activity_title),
            SlotSet("activity3_name",
                    rnd_activities[2].intervention_activity_title),
            SlotSet("rnd_activities_ids", rnd_activities_ids),
        ]


class ValidateGeneralActivityNextActivityForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_general_activity_next_activity_form"

    def validate_general_activity_next_activity_slot(
        self, value: Text, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_next_activity_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != "utter_ask_general_activity_next_activity_slot":
            return {"general_activity_next_activity_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"general_activity_next_activity_slot": None}

        if value == "4":
            activity_id = tracker.get_slot("last_activity_id_slot")

            rnd_activities = get_random_activities(activity_id, 3)
            rnd_activities_ids = [
                activity.intervention_activity_id for activity in rnd_activities]

            return {
                "general_activity_next_activity_slot": None,
                "activity1_name": rnd_activities[0].intervention_activity_title,
                "activity2_name": rnd_activities[1].intervention_activity_title,
                "activity3_name": rnd_activities[2].intervention_activity_title,
                "rnd_activities_ids": rnd_activities_ids,
            }

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
        # get the last completed activity from DB and populate the slot

        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()["sender_id"]
        last_activity = (
            session.query(InterventionActivitiesPerformed)
            .order_by(InterventionActivitiesPerformed.completed_datetime.desc())
            .filter(InterventionActivitiesPerformed.users_nicedayuid == user_id)
            .all()
        )

        if last_activity is not None and len(last_activity) != 0:
            activity_title = last_activity[0].intervention_activity.intervention_activity_title
            activity_id = last_activity[0].intervention_activity.intervention_activity_id
            return [SlotSet("last_activity_slot", activity_title),
                    SlotSet("last_activity_id_slot", activity_id)]

        return [SlotSet("last_activity_slot", None),
                SlotSet("last_activity_id_slot", None)]


class GetActivityCoachChoice(Action):
    """The coach chooses the next activity and saves it in the slot"""

    def name(self):
        return "get_activity_coach_choice"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, returns a random title
        # TODO: implement logic

        return [SlotSet("chosen_activity_slot", "this is the chosen activity")]


class CheckWhoDecides(Action):
    """Check if the user or the coach decides the next activity"""

    def name(self):
        return "check_who_decides"

    async def run(self, dispatcher, tracker, domain):
        # for testing purposes, the user decides
        # TODO: implement logic

        decider = "user"

        return [SlotSet("who_decides_slot", decider)]


class LoadActivity(Action):
    """load the activity instructions"""

    def name(self):
        return "load_activity"

    async def run(self, dispatcher, tracker, domain):

        chosen_option = int(tracker.get_slot(
            "general_activity_next_activity_slot"))
        activities_slot = tracker.get_slot("rnd_activities_ids")
        user_id = tracker.current_state()["sender_id"]

        activity_id = activities_slot[chosen_option - 1]
        session = get_db_session(db_url=DATABASE_URL)

        user_inputs = get_user_intervention_activity_inputs(
            user_id, activity_id)

        if user_inputs:
            previous_input = user_inputs[-1].user_input
        else:
            previous_input = None

        # save the activity to the DB
        session.add(
            InterventionActivitiesPerformed(
                users_nicedayuid=user_id,
                intervention_activity_id=activity_id,
                user_input=previous_input))

        session.commit()

        # get the instructions
        instructions = (
            session.query(InterventionActivity)
            .filter(InterventionActivity.intervention_activity_id == activity_id)
            .all()
        )

        # prompt the message
        # FIXME: what if there is no instructions
        dispatcher.utter_message(
            text=instructions[0].intervention_activity_full_instructions)
        return []


class SetSlotGeneralActivity(Action):
    def name(self):
        return "action_set_slot_general_activity"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        ExecutionInterventionComponents.GENERAL_ACTIVITY)]


def save_activity_to_fak(user_id: int, activity_id: int, rating_value: int):
    session = get_db_session(db_url=DATABASE_URL)

    session.add(
        FirstAidKit(
            users_nicedayuid=user_id,
            intervention_activity_id=activity_id,
            activity_rating=rating_value))
    session.commit()


def get_user_intervention_activity_inputs(user_id: int, activity_id: int):
    session = get_db_session(db_url=DATABASE_URL)

    user_inputs = (
        session.query(InterventionActivitiesPerformed) .filter(
            InterventionActivitiesPerformed.users_nicedayuid == user_id,
            InterventionActivitiesPerformed.intervention_activity_id == activity_id,
        ) .all())

    return user_inputs


def get_random_activities(avoid_activity_id: int, number_of_activities: int):
    session = get_db_session(db_url=DATABASE_URL)

    available_activities = (
        session.query(InterventionActivity)
        .filter(InterventionActivity.intervention_activity_id != avoid_activity_id)
        .all()
    )
    # FIXME: what if the len(available_activities) < number_of_activities

    rnd_activities = []

    for _ in range(number_of_activities):
        random_choice = secrets.choice(available_activities)
        rnd_activities.append(random_choice)
        available_activities.remove(random_choice)

    return rnd_activities
