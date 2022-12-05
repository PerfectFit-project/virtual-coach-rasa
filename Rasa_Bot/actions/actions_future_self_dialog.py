"""
Contains custom actions related to the future self dialog
"""
import datetime
import logging
import string
from typing import Any, Dict, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from sqlalchemy import func
from virtual_coach_db.helper.helper_functions import get_db_session
from virtual_coach_db.helper.definitions import PreparationInterventionComponents
# from virtual_coach_db.dbschema.models import (Users, DialogAnswers, UserInterventionState,
#                                               InterventionComponents)

from .definitions import DialogQuestions, TIMEZONE, DATABASE_URL
# from .helper import (store_dialog_answer_to_db,
#                                     get_intervention_component_id)


class SetSlotFutureSelfDialog(Action):
    def name(self):
        return "action_set_slot_future_self_dialog"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        PreparationInterventionComponents.FUTURE_SELF)]


class ActionStoreSmokerWords(Action):
    """"To save user input on smoker words from future self dialog to database"""

    def name(self):
        return "action_store_smoker_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("picked_words")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer, DialogQuestions.FUTURE_SELF_SMOKER_WORDS)
        return


class ActionStoreMoverWords(Action):
    """"To save user input on mover words from future self dialog to database"""

    def name(self):
        return "action_store_mover_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("picked_words")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer, DialogQuestions.FUTURE_SELF_MOVER_WORDS)
        return


class ActionStoreWhyMoverWords(Action):
    """"To save user input on why he/she chose mover words from future self dialog to database"""

    def name(self):
        return "action_store_why_mover_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("why_picked_words")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer, DialogQuestions.FUTURE_SELF_MOVER_WHY)
        return


class ActionStoreWhySmokerWords(Action):
    """"To save user input on why he/she chose smoker words from future self dialog to database"""

    def name(self):
        return "action_store_why_smoker_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("why_picked_words")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer, DialogQuestions.FUTURE_SELF_SMOKER_WHY)
        return


class ActionStoreSeeMyselfAsPickedSmokerWords(Action):
    """"To save user input on how they see themselves as smoker in future self dialog to database"""

    def name(self):
        return "action_store_see_myself_as_picked_smoker_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("see_myself_as_picked_words_smoker")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer,
                                  DialogQuestions.FUTURE_SELF_I_SEE_MYSELF_AS_SMOKER)
        return


class ActionStoreSeeMyselfAsPickedMoverWords(Action):
    """"To save user input on how they see themselves as mover in future self dialog to database"""

    def name(self):
        return "action_store_see_myself_as_picked_mover_words"

    async def run(self, dispatcher, tracker, domain):
        answer = tracker.get_slot("see_myself_as_picked_words_mover")
        user_id = tracker.current_state()['sender_id']
        store_dialog_answer_to_db(user_id, answer,
                                  DialogQuestions.FUTURE_SELF_I_SEE_MYSELF_AS_MOVER)
        return


class ActionResetPickedWordsSlot(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_picked_words_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("picked_words", None)]


class ActionResetWhyPickedWordsSlotSmoking(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_why_picked_words_slot_smoking"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("why_picked_words", None)]


class ActionResetWhyPickedWordsSlotPA(Action):
    """Reset picked_words slot"""

    def name(self):
        return "action_reset_why_picked_words_slot_pa"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("why_picked_words", None)]


class ActionResetConfirmWordsResponseSlotSmoking(Action):
    """Reset confirm_words_response slot"""

    def name(self):
        return "action_reset_confirm_words_response_slot_smoking"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("confirm_words_response", None)]


class ActionResetConfirmWordsResponseSlotPA(Action):
    """Reset confirm_words_response slot"""

    def name(self):
        return "action_reset_confirm_words_response_slot_pa"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("confirm_words_response", None)]


def validate_yes_no_response(value):
    if value.lower() == 'ja':
        return True
    if value.lower() in ['nee', "nee."]:
        return False
    return None


class ValidateConfirmWordsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_confirm_words_form'

    def validate_confirm_words_response(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate yes_or_no_response input."""

        yes_or_no_response = validate_yes_no_response(value)
        if yes_or_no_response is None:
            dispatcher.utter_message(response="utter_please_answer_yes_no")

        return {"confirm_words_response": yes_or_no_response}


class ValidateSeeMyselfAsSmokerForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_see_myself_as_smoker_form'

    def validate_see_myself_as_picked_words_smoker(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate see_myself_as_picked_words_smoker input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"see_myself_as_picked_words_smoker": None}

        return {"see_myself_as_picked_words_smoker": int(value)}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 3):
            return False
        return True


class ActionMapSeeMyselfAsPickedWordsSmoker(Action):
    """Map see_myself_as_picked_words_smoker slot to text"""

    def name(self):
        return "action_map_see_myself_as_picked_words_smoker"

    async def run(self, dispatcher, tracker, domain):

        num = tracker.get_slot('see_myself_as_picked_words_smoker')

        if num == 1:
            text = "een roker"
        elif num == 2:
            text = "een niet-roker"
        else:
            text = "iemand die stopt met roken"

        return [SlotSet("see_myself_as_picked_words_smoker_text", text)]


class ActionResetSeeMyselfAsPickedWordsSmoker(Action):
    """Reset see_myself_as_picked_words_smoker slot"""

    def name(self):
        return "action_reset_see_myself_as_picked_words_smoker"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("see_myself_as_picked_words_smoker", None)]


class ValidateSeeMyselfAsMoverForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_see_myself_as_mover_form'

    def validate_see_myself_as_picked_words_mover(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate see_myself_as_picked_words_mover input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"see_myself_as_picked_words_mover": None}

        return {"see_myself_as_picked_words_mover": int(value)}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 3):
            return False
        return True


class ActionMapSeeMyselfAsPickedWordsMover(Action):
    """Map see_myself_as_picked_words_mover slot to text"""

    def name(self):
        return "action_map_see_myself_as_picked_words_mover"

    async def run(self, dispatcher, tracker, domain):

        num = tracker.get_slot('see_myself_as_picked_words_mover')

        if num == 1:
            text = "lichamelijk actief"
        elif num == 2:
            text = "een beetje lichamelijk actief"
        else:
            text = "niet lichamelijk actief"

        return [SlotSet("see_myself_as_picked_words_mover_text", text)]


class ActionResetSeeMyselfAsPickedWordsMover(Action):
    """Reset see_myself_as_picked_words_mover slot"""

    def name(self):
        return "action_reset_see_myself_as_picked_words_mover"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("see_myself_as_picked_words_mover", None)]


def validate_long_enough_response(response):
    if response is None:
        return False
    return len(simple_sanitize_input(response).split()) > 5


def simple_sanitize_input(value):
    return value.translate({c: "" for c in string.punctuation})


class ValidateWhyPickedMoverWordsForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_why_picked_mover_words_form"

    def validate_why_picked_words(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate validate_why_picked_words input."""

        long_enough_response = validate_long_enough_response(value)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"why_picked_words": None}

        logging.info(
            "%s why_picked_words: %s", type(self).__name__, long_enough_response
        )
        return {"why_picked_words": value}


class ValidateWhyPickedSmokerWordsForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_why_picked_smoker_words_form"

    def validate_why_picked_words(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate validate_why_picked_words input."""

        long_enough_response = validate_long_enough_response(value)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"why_picked_words": None}

        logging.info(
            "%s why_picked_words: %s ", type(self).__name__, long_enough_response
        )
        return {"why_picked_words": value}


class ActionSetFutureSelfDialogStateStep1(Action):
    """To set state of future self dialog to step 1"""

    def name(self):
        return "action_set_future_self_dialog_state_step_1"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("future_self_dialog_state", 1)]


def get_most_recent_question_answer_from_database(session, user_id,
                                                  question_id):
    """To get chosen words from last run of future self dialog from database"""

    subquery = (
        session.query(
            func.max(DialogAnswers.datetime)
        )
        .filter(
            DialogAnswers.users_nicedayuid == user_id,
            DialogAnswers.question_id == question_id
        )
    )

    query = (
        session.query(
            DialogAnswers
        )
        .filter(
            DialogAnswers.users_nicedayuid == user_id,
            DialogAnswers.question_id == question_id,
            DialogAnswers.datetime == subquery
        )
        .first()
    )

    words = query.answer

    return words


class ActionGetFutureSelfRepetitionFromDatabase(Action):
    """To get from database whether this is a repetition of the
        future self dialog and if yes, the relevant saved
        responses from the previous time."""

    def name(self):
        return "action_get_future_self_repetition_from_database"

    async def run(self, dispatcher, tracker, domain):
        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()['sender_id']
        future_self_value = PreparationInterventionComponents.FUTURE_SELF.value

        selected = (
            session.query(
                UserInterventionState
            )
            .join(InterventionComponents)
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                InterventionComponents.intervention_component_name == future_self_value
            )
            .filter(
                UserInterventionState.users_nicedayuid == user_id
            )
            .first()
        )

        # If already an entry for the user for the future self dialog exists
        # in the intervention state table
        if selected is not None:
            # Get most recent saved chosen smoker words
            question_id = DialogQuestions.FUTURE_SELF_SMOKER_WORDS.value
            smoker_words = get_most_recent_question_answer_from_database(session,
                                                                         user_id,
                                                                         question_id)

            # Same for mover
            question_id = DialogQuestions.FUTURE_SELF_MOVER_WORDS.value
            mover_words = get_most_recent_question_answer_from_database(session,
                                                                        user_id,
                                                                        question_id)

            return [SlotSet("future_self_dialog_step_1_repetition", True),
                    SlotSet("future_self_dialog_smoker_words_prev", smoker_words),
                    SlotSet("future_self_dialog_mover_words_prev", mover_words)]

        # No entry exists yet for user for the future self dialog in
        # the intervention state table
        return [SlotSet("future_self_dialog_step_1_repetition", False)]


class ActionStoreFutureSelfDialogState(Action):
    """To save state of future self dialog"""

    def name(self):
        return "action_store_future_self_dialog_state"

    async def run(self, dispatcher, tracker, domain):
        step = tracker.get_slot("future_self_dialog_state")
        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()['sender_id']
        future_self_value = PreparationInterventionComponents.FUTURE_SELF.value

        selected = (
            session.query(
                UserInterventionState
            )
            .join(InterventionComponents)
            .filter(
                UserInterventionState.users_nicedayuid == user_id,
                InterventionComponents.intervention_component_name == future_self_value
            )
            .first()
        )

        # Current time to be saved in database
        last_time = datetime.datetime.now().astimezone(TIMEZONE)

        # If already an entry for the user for the future self dialog exists
        # in the intervention state table
        if selected is not None:
            # Update time and part of future self dialog
            selected.last_time = last_time
            selected.last_part = step

        # No entry exists yet for user for the future self dialog in
        # the intervention state table
        else:
            intervention_component_id = \
                get_intervention_component_id(PreparationInterventionComponents.FUTURE_SELF)
            selected_user = session.query(Users).filter_by(nicedayuid=user_id).one_or_none()

            # User exists in Users table
            if selected_user is not None:
                entry = UserInterventionState(intervention_component_id=intervention_component_id,
                                              last_time=last_time,
                                              last_part=step)
                selected_user.user_intervention_state.append(entry)

            # User does not exist in Users table
            else:
                logging.error("Error: User not in Users table")

        session.commit()  # Update database

        return []
