import random
import secrets

from sqlalchemy import update
from virtual_coach_db.dbschema.models import (InterventionActivitiesPerformed, 
                                              FirstAidKit,
                                              InterventionActivity)
from virtual_coach_db.helper import (ExecutionInterventionComponents, 
                                     DialogQuestionsEnum)
from virtual_coach_db.helper.helper_functions import get_db_session
from .definitions import (COMMITMENT, CONSENSUS, DATABASE_URL, NUM_TOP_ACTIVITIES, 
                          OPT_POLICY, STATE_FEATURE_MEANS)
from .helper import get_latest_bot_utterance, store_dialog_closed_answer_to_db
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import Any, Dict, Text


class CheckIfFirstExecutionGA(Action):
    """Check if it is the first execution"""

    def name(self):
        return "check_if_first_execution_ga"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()['sender_id']
        session = get_db_session(db_url=DATABASE_URL)

        performed_activity = (
            session.query(
                InterventionActivitiesPerformed
            )
            .filter(
                InterventionActivitiesPerformed.users_nicedayuid == user_id
            )
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

        rating_value = int(tracker.get_slot('activity_useful_rating'))
        activity_id = int(tracker.get_slot('last_activity_id_slot'))

        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()['sender_id']

        # get the highest scored activities
        top_five_activities = (
            session.query(
                FirstAidKit
            ).order_by(FirstAidKit.activity_rating.desc())
            .filter(
                FirstAidKit.users_nicedayuid == user_id
            )
            .limit(NUM_TOP_ACTIVITIES).all()
        )

        current_record = (
            session.query(
                FirstAidKit
            )
            .filter(
                FirstAidKit.users_nicedayuid == user_id,
                FirstAidKit.intervention_activity_id == activity_id
            )
            .all()
        )

        lowest_score = top_five_activities[-1].activity_rating

        # if the activity is not in the FAK, add it
        if not current_record:

            save_activity_to_fak(user_id, activity_id, rating_value)

            session.commit()

            return [SlotSet("general_activity_low_high_rating", 'high')]

        # update the row containing the activity with the new rating
        session.execute(
            update(FirstAidKit)
            .where(FirstAidKit.first_aid_kit_id == current_record[0].first_aid_kit_id)
            .values(activity_rating=rating_value)
        )

        session.commit()

        if rating_value > lowest_score:
            return [SlotSet("general_activity_low_high_rating", 'high')]

        return [SlotSet("general_activity_low_high_rating", 'low')]


class GetActivityUserInput(Action):
    """Get the user input and save it in the slot"""

    def name(self):
        return "get_activity_user_input"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)
        last_input = user_inputs[-1].user_input

        return [SlotSet("activity_user_input", last_input)]


class CheckUserInputRequired(Action):
    """Check if the activity requires the input of the user"""

    def name(self):
        return "check_user_input_required"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot('last_activity_id_slot')
        session = get_db_session(db_url=DATABASE_URL)

        is_input_required = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )

        return [SlotSet("is_user_input_required", is_input_required[0].user_input_required)]


class CheckActivityDone(Action):
    """Check if an input for the activity has been
    already provided by the user"""

    def name(self):
        return "check_activity_done"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)

        if user_inputs[-1].user_input is None:
            activity_done = False
        else:
            activity_done = True

        return [SlotSet("is_activity_done", activity_done)]


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
        if value in ('1', '2'):
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
        """Save the provided description inf the DB."""

        description = tracker.get_slot('general_activity_description_slot')

        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)
        row_id = user_inputs[-1].intervention_activities_performed_id

        session = get_db_session(db_url=DATABASE_URL)

        session.execute(
            update(InterventionActivitiesPerformed)
            .where(InterventionActivitiesPerformed.intervention_activities_performed_id == row_id)
            .values(
                user_input=description
            )
        )

        session.commit()

        return []


class GetThreeRandomActivities(Action):
    def name(self) -> Text:
        return 'get_three_random_activities'

    async def run(self, dispatcher, tracker, domain):
        """pick three random activities and sets the slots"""

        activity_id = tracker.get_slot('last_activity_id_slot')

        rnd_activities = get_random_activities(activity_id, 3)
        rnd_activities_ids = [activity.intervention_activity_id for activity in rnd_activities]

        return [SlotSet("activity1_name", rnd_activities[0].intervention_activity_title),
                SlotSet("activity2_name", rnd_activities[1].intervention_activity_title),
                SlotSet("activity3_name", rnd_activities[2].intervention_activity_title),
                SlotSet("rnd_activities_ids", rnd_activities_ids)]


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
            activity_id = tracker.get_slot('last_activity_id_slot')

            rnd_activities = get_random_activities(activity_id, 3)
            rnd_activities_ids = [activity.intervention_activity_id for activity in rnd_activities]

            return {"general_activity_next_activity_slot": None,
                    "activity1_name": rnd_activities[0].intervention_activity_title,
                    "activity2_name": rnd_activities[1].intervention_activity_title,
                    "activity3_name": rnd_activities[2].intervention_activity_title,
                    "rnd_activities_ids": rnd_activities_ids}

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
        user_id = tracker.current_state()['sender_id']
        last_activity = (
            session.query(
                InterventionActivitiesPerformed
            )
            .order_by(InterventionActivitiesPerformed.completed_datetime.desc())
            .filter(
                InterventionActivitiesPerformed.users_nicedayuid == user_id
            ).all()
        )

        if last_activity is not None:
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

        decider = 'user'

        return [SlotSet("who_decides_slot", decider)]


class LoadActivity(Action):
    """load the activity instructions"""

    def name(self):
        return "load_activity"

    async def run(self, dispatcher, tracker, domain):

        chosen_option = int(tracker.get_slot('general_activity_next_activity_slot'))
        activities_slot = tracker.get_slot('rnd_activities_ids')
        user_id = tracker.current_state()['sender_id']

        activity_id = activities_slot[chosen_option - 1]
        session = get_db_session(db_url=DATABASE_URL)

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)

        if user_inputs:
            previous_input = user_inputs[-1].user_input
        else:
            previous_input = None

        # save the activity to the DB
        session.add(
            InterventionActivitiesPerformed(users_nicedayuid=user_id,
                                            intervention_activity_id=activity_id,
                                            user_input=previous_input)
        )

        session.commit()

        # get the instructions
        instructions = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )

        # prompt the message
        dispatcher.utter_message(text=instructions[0].intervention_activity_full_instructions)
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
        FirstAidKit(users_nicedayuid=user_id,
                    intervention_activity_id=activity_id,
                    activity_rating=rating_value)
    )
    session.commit()


def get_user_intervention_activity_inputs(user_id: int, activity_id: int):
    session = get_db_session(db_url=DATABASE_URL)

    user_inputs = (
        session.query(
            InterventionActivitiesPerformed
        )
        .filter(
            InterventionActivitiesPerformed.users_nicedayuid == user_id,
            InterventionActivitiesPerformed.intervention_activity_id == activity_id
        ).all()
    )

    return user_inputs


def get_random_activities(avoid_activity_id: int, number_of_activities: int):
    session = get_db_session(db_url=DATABASE_URL)

    available_activities = (
        session.query(
            InterventionActivity
        )
        .filter(
            InterventionActivity.intervention_activity_id != avoid_activity_id
        )
        .all()
    )

    rnd_activities = []

    for _ in range(number_of_activities):
        random_choice = secrets.choice(available_activities)
        rnd_activities.append(random_choice)
        available_activities.remove(random_choice)

    return rnd_activities


class ValidatePersuasionReflectionForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_reflection_form'

    def validate_persuasion_reflection_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_reflection_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_reflection_slot':
            return {"persuasion_want_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"persuasion_reflection_slot": None}

        return {"persuasion_reflection_slot": value}

    @staticmethod
    def _validate_response_value(value):
        if len(value) >= 10:
            return True
        return False
    
    
class SavePersuasionToDatabase(Action):
    """Save persuasion to database"""

    def name(self):
        return "save_persuasion_to_database"

    async def run(self, dispatcher, tracker, domain):
    
        user_id = tracker.current_state()['sender_id']
        
        # Get chosen persuasion type
        pers_type = tracker.get_slot('persuasion_type')
        # Get index of chosen persuasive message; -1 if "no persuasion"
        message_idx = tracker.get_slot("persuasive_message_index")
        # Get answers to state feature questions
        want = tracker.get_slot('persuasion_want_slot')
        prompts = tracker.get_slot('persuasion_prompts_slot')
        need = tracker.get_slot('persuasion_need_slot')
        
        # Store state feature values to database
        store_dialog_closed_answer_to_db(user_id, answer_value = want, question_id = DialogQuestionsEnum.PERSUASION_WANT)
        store_dialog_closed_answer_to_db(user_id, answer_value = need, question_id = DialogQuestionsEnum.PERSUASION_NEED)
        store_dialog_closed_answer_to_db(user_id, answer_value = prompts, question_id = DialogQuestionsEnum.PERSUASION_PROMPTS)
        # Answer_values must start at 1
        store_dialog_closed_answer_to_db(user_id, answer_value = pers_type + 1, question_id = DialogQuestionsEnum.PERSUASION_TYPE)
        # +2 since the lowest value we have is -1 in case of no persuasion
        store_dialog_closed_answer_to_db(user_id, answer_value = message_idx + 2, question_id = DialogQuestionsEnum.PERSUASION_MESSAGE_INDEX)

        return []


class SendPersuasiveMessageActivity(Action):
    """Choose persuasion type and send persuasive message (if any)"""

    def name(self):
        return "send_persuasive_message_activity"

    async def run(self, dispatcher, tracker, domain):
        
        chosen_option = int(tracker.get_slot('general_activity_next_activity_slot'))
        activities_slot = tracker.get_slot('rnd_activities_ids')

        activity_id = activities_slot[chosen_option - 1]
        session = get_db_session(db_url=DATABASE_URL)

        # Get the activity benefit
        activities = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )
        benefit = activities[0].intervention_activity_benefit
        
        # Get answers to state feature questions
        want = tracker.get_slot('persuasion_want_slot')
        prompts = tracker.get_slot('persuasion_prompts_slot')
        need = tracker.get_slot('persuasion_need_slot')
        
        # Make state binary
        binary_state = [want >= STATE_FEATURE_MEANS[0], prompts >= STATE_FEATURE_MEANS[1], 
                        need >= STATE_FEATURE_MEANS[2]]
        
        # Get optimal persuasion type
        pers_type = OPT_POLICY[binary_state[0]][binary_state[1]][binary_state[2]]
        
        reflective_question = ""  # Relfective question to ask users as part of persuasion
        input_required = False  # Whether we will ask a reflective question to users
        message_idx = -1  # Index of persuasive message
        # Commitment
        if pers_type == 0:
            input_required = True
            message_idx = random.choice([i for i in range(len(COMMITMENT))])
            message = COMMITMENT[message_idx]
            dispatcher.utter_message(text=message)
            # Not identity-based formulation
            if message_idx < 4:
                reflective_question = "Please tell me what you think: In what way does doing this activity match your decision to successfully quit smoking?"
            # Identity-based formulation
            else:
                reflective_question = "Please tell me what you think: In what way does doing this activity match your decision to become somebody who has successfully quit smoking?"
        # Consensus
        elif pers_type == 1:
            input_required = True
            message_idx = random.choice([i for i in range(len(CONSENSUS))])
            message = CONSENSUS[message_idx] + benefit
            dispatcher.utter_message(text=message)
            reflective_question = "Please tell me what you think: How would people like you, in a situation like yours, agree with this?"
        
        return [SlotSet("persuasion_type", pers_type),
                SlotSet("persuasive_message_index", message_idx),
                SlotSet("persuasion_requires_input", input_required),
                SlotSet("persuasion_reflective_question", reflective_question)]
    

class ValidatePersuasionWantForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_want_form'

    def validate_persuasion_want_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_want_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_want_slot':
            return {"persuasion_want_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_want_slot": None}

        return {"persuasion_want_slot": value}

    @staticmethod
    def _validate_response_value(value):
        if 1 <= int(value) <= 5:
            return True
        return False
    
    
class ValidatePersuasionNeedForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_need_form'

    def validate_persuasion_need_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_need_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_need_slot':
            return {"persuasion_need_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_need_slot": None}

        return {"persuasion_need_slot": value}

    @staticmethod
    def _validate_response_value(value):
        if 1 <= int(value) <= 5:
            return True
        return False
    

class ValidatePersuasionPromptsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_prompts_form'

    def validate_persuasion_prompts_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_prompts_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_prompts_slot':
            return {"persuasion_prompts_slot": None}

        if not self._validate_response_value(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_prompts_slot": None}

        return {"persuasion_prompts_slot": value}

    @staticmethod
    def _validate_response_value(value):
        if 1 <= int(value) <= 5:
            return True
        return False