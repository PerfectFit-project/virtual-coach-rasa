# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
import datetime
import logging
import os
import string
from enum import Enum
from typing import Any, Dict, Text

from dateutil import tz
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from niceday_client import NicedayClient, definitions
from paalgorithms import weekly_kilometers
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from sqlalchemy import func
from virtual_coach_db.dbschema.models import (Users, ClosedUserAnswers, DialogAnswers,
                                              FirstAidKit, UserInterventionState)
from virtual_coach_db.helper.helper import get_db_session

# load database url and niceday_api_endopint variables
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')

# Timezone for saving data to database
TIMEZONE = tz.gettz("Europe/Amsterdam")


class DialogQuestions(Enum):
    FUTURE_SELF_SMOKER_WORDS = 1  # Which three words suits you as smoker?
    FUTURE_SELF_SMOKER_WHY = 2  # Why did you pick these words for smoking?
    FUTURE_SELF_MOVER_WORDS = 3  # Which three words suits you as exerciser?
    FUTURE_SELF_MOVER_WHY = 4  # Why did you pick these words for exercising?
    FUTURE_SELF_I_SEE_MYSELF_AS_SMOKER = 5  # I see myself as smoker, non-smoker or quitter
    FUTURE_SELF_I_SEE_MYSELF_AS_MOVER = 6  # I see myself as active, bit active or not active


def store_dialog_answer_to_db(user_id, answer, question: DialogQuestions):
    session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db
    selected = session.query(Users).filter_by(nicedayuid=user_id).one()

    entry = DialogAnswers(answer=answer,
                          question_id=question.value,
                          datetime=datetime.datetime.now().astimezone(TIMEZONE))

    selected.dialog_answers.append(entry)
    session.commit()  # Update database


# Get the user's age from the database.
# Save the extracted age to a slot.
class GetAgeFromDatabase(Action):
    def name(self):
        return "action_get_age_from_database"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()['sender_id']

        # Create session object to connect db
        session = get_db_session(db_url=DATABASE_URL)

        try:
            user_id = int(user_id)  # nicedayuid is an integer in the database
            selected = session.query(Users).filter_by(nicedayuid=user_id).one()
            dob = selected.dob
            today = datetime.date.today()

            # calculate age in years
            age = relativedelta(today, dob).years

        # invalid ID for database
        except ValueError as e:
            age = 18
            logging.error("ValueError: failed to get user age from database. "
                          "User ID could not be converted to int: %s", e)

        except Exception as e:
            age = 18
            logging.error("Failed to get user age from "
                          "database: %s - Defaulting to age 18.", e)

        finally:
            session.close()

        return [SlotSet("age", age)]


# Get the user's name from the database.
# Save the extracted name to a slot.
class GetNameFromDatabase(Action):
    def name(self):
        return "action_get_name_from_database"

    async def run(self, dispatcher, tracker, domain):

        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']

        # Creat session object to connect db
        session = get_db_session(db_url=DATABASE_URL)

        try:
            user_id = int(user_id)  # nicedayuid is an integer in the database
            selected = session.query(Users).filter_by(nicedayuid=user_id).one()
            name = selected.firstname

        # invalid ID for database
        except ValueError as e:
            name = 'Perfect Fit user'
            logging.error("ValueError: failed to get user name from database. "
                          "User ID could not be converted to int: %s.", e)

        except Exception as e:
            name = 'Perfect Fit user'
            logging.error("Failed to get user name from "
                          "database: %s - Defaulting to "
                          "Perfect Fit user.", e)

        finally:
            session.close()

        return [SlotSet("name", name)]


# Get weekly plan
class GetPlanWeek(Action):
    def name(self):
        return "action_get_plan_week"

    async def run(self, dispatcher, tracker, domain):

        age = tracker.get_slot("age")

        # Calculates weekly kilometers based on age
        kilometers = weekly_kilometers(age)
        plan = f"Sure, you should run {kilometers:.1f} kilometers this week. " \
               "And please read through this " \
               "psycho-education: www.link-to-psycho-education.nl."
        return [SlotSet("plan_week", plan)]


# Get number of cigarettes from custom tracker and save in slot
class SaveNumberCigarettes(Action):
    def name(self):
        return "action_save_number_cigarettes"

    async def run(self, dispatcher, tracker, domain):

        client = NicedayClient(NICEDAY_API_ENDPOINT)

        # get the user_id
        user_id = int(tracker.current_state()['sender_id'])

        # get the time of the request (final time point)
        current_time = datetime.datetime.now()

        # set the initial time point as the beginning of current day
        today = datetime.date.today()
        start_time = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)

        # query the niceday_client api to get the number of tracked cigarettes
        number_cigarettes_response = client.get_smoking_tracker(user_id, start_time, current_time)

        # iterate through the response to get the total number of tracked cigarettes
        number_of_cigarettes = 0
        for item in number_cigarettes_response:
            number_of_cigarettes += item['value']['quantity']

        return [SlotSet("number_of_cigarettes", number_of_cigarettes)]


# Get number of cigarettes from slot
class GetNumberCigarettes(Action):
    def name(self):
        return "action_get_number_cigarettes"

    async def run(self, dispatcher, tracker, domain):

        number_of_cigarettes = tracker.get_slot("number_of_cigarettes")
        dispatcher.utter_message(response="utter_tracked_cigarettes",
                                 number_of_cigarettes=number_of_cigarettes)
        return[]


# Save weekly plan in calendar
class SavePlanWeekCalendar(Action):
    def name(self):
        return "action_save_plan_week_calendar"

    async def run(self, dispatcher, tracker, domain):

        success = True

        return [SlotSet("success_save_calendar_plan_week", success)]


# Validate input of liker scale form
class ValidatePaEvaluationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_evaluation_form'

    def validate_pa_evaluation_response(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_evaluation_response input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_please_answer_1_to_5")
            return {"pa_evaluation_response": None}
        pa_evaluation_response = int(value)
        return {"pa_evaluation_response": pa_evaluation_response}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 5):
            return False
        return True


# Have a custom response based on the pa_evaluation response
class ActionUtterPaEvaluationFormFilled(Action):
    """Custom response based on PA evaluation form"""

    def name(self):
        return "action_utter_pa_evaluation_form_filled"

    async def run(self, dispatcher, tracker, domain):
        pa_evaluation_response = tracker.get_slot("pa_evaluation_response")

        if pa_evaluation_response >= 4:
            dispatcher.utter_message(response="utter_feedback_pa_evaluation_high")
        else:
            dispatcher.utter_message(response="utter_feedback_pa_evaluation_low")
        return []


class ActionStorePaEvaluation(Action):
    """"To save user input from PA evaluation form to database"""

    def name(self):
        return "action_store_pa_evaluation"

    async def run(self, dispatcher, tracker, domain):

        pa_evaluation_response = tracker.get_slot("pa_evaluation_response")
        session = get_db_session(db_url=DATABASE_URL)  # Create session object to connect db

        user_id = tracker.current_state()['sender_id']
        selected = session.query(Users).filter_by(nicedayuid=user_id).one()

        entry = ClosedUserAnswers(value=pa_evaluation_response,
                                  question='paevaluation',
                                  datetime=datetime.datetime.now().astimezone(TIMEZONE))
        selected.closed_user_answers.append(entry)
        session.commit()  # Update database
        
        return [SlotSet("pa_evaluation_response", None)]


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


class ActionResetReschedulingNowSlot(Action):
    """Reset rescheduling_now slot"""

    def name(self):
        return "action_reset_rescheduling_now_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("rescheduling_now", None)]


class ValidateReschedulingNowOrLaterForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_rescheduling_now_or_later_form'

    def validate_rescheduling_now(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate rescheduling_now input."""

        now_or_later = self._validate_now_or_later_response(value)
        if now_or_later is None:
            dispatcher.utter_message(response="utter_please_answer_now_or_later")

        return {"rescheduling_now": now_or_later}

    @staticmethod
    def _validate_now_or_later_response(value):
        if value.lower() in ['nu', 'nou', 'nu is goed']:
            return True
        if value.lower() in ['later', 'later.', 'niet nu']:
            return False
        return None
    

class ActionGetReschedulingOptionsList(Action):
    """Get the possible rescheduling options."""
    
    def name(self):
        return "action_get_rescheduling_options_list"
    
    async def run(self, dispatcher, tracker, domain):
        
        # define morning, afternoon, evening
        MORNING = (6, 12)
        AFTERNOON = (12, 18)
        EVENING = (18, 24)
        
        options = ["In een uur"]
        
        current_hour = datetime.datetime.now().astimezone(TIMEZONE).hour
        
        
        # In the morning
        if MORNING[0] <= current_hour < MORNING[1]:
            options +=  ["Vanmiddag, om 16:00",
                         "Vanavond, om 21:00",
                         "Morgenochtend om deze tijd"]
        # In the afternoon
        elif AFTERNOON[0] <= current_hour < AFTERNOON[1]:
            options += ["Vanavond, om 21:00",
                        "Morgenochtend, om 8:00",
                        "Morgenmiddag om deze tijd"]
        # In the evening
        elif EVENING[0] <= current_hour < EVENING[1]:
            options += ["Morgenochtend, om 8:00",
                        "Morgenmiddag, om 16:00",
                        "Morgenavond om deze tijd"]
        # In the night
        else:
            options +=  ["Vanmiddag, om 16:00",
                         "Vanavond, om 21:00",
                         "Morgen om deze tijd"]
        
        # Create string of options to utter them
        num_options = len(options)
        rescheduling_options_string = ""
        for o in range(num_options):
            rescheduling_options_string += "(" + str(o + 1) + ") " + options[o] + "."
            if not o == len(options) - 1:
                rescheduling_options_string += " "
        
        return [SlotSet("rescheduling_options_list", options),
                SlotSet("rescheduling_options_string", 
                        rescheduling_options_string)]


class ActionResetReschedulingOptionSlot(Action):
    """Reset rescheduling_option slot"""

    def name(self):
        return "action_reset_rescheduling_option_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("rescheduling_option", None)]


class ValidateReschedulingOptionsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_rescheduling_options_form'

    def validate_rescheduling_option(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate rescheduling_option input."""

        if not self._is_valid_input(value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"rescheduling_option": None}

        return {"rescheduling_option": int(value)}

    @staticmethod
    def _is_valid_input(value):
        try:
            value = int(value)
        except ValueError:
            return False
        if (value < 1) or (value > 4):
            return False
        return True


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
            return{"why_picked_words": None}

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

    subquery =  (
        session.query(
           func.max(DialogAnswers.datetime)
        )
        .filter(
            DialogAnswers.users_nicedayuid==user_id,
            DialogAnswers.question_id==question_id
        )
    )

    query =  (
        session.query(
           DialogAnswers
        )
        .filter(
            DialogAnswers.users_nicedayuid==user_id,
            DialogAnswers.question_id==question_id,
            DialogAnswers.datetime==subquery
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

        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid==user_id, 
                UserInterventionState.intervention_component=="future_self_dialog"
            )
            .one_or_none()
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
        selected = (
            session.query(
                UserInterventionState
            )
            .filter(
                UserInterventionState.users_nicedayuid==user_id, 
                UserInterventionState.intervention_component=="future_self_dialog"
            )
            .one_or_none()
        )
        
        # Current time to be saved in database
        last_time = datetime.datetime.now().astimezone(TIMEZONE)

        # If already an entry for the user for the future self dialog exists
        # in the intervention state table
        if selected is not None:
            # Update time and part of future self dialog
            selected.last_time=last_time
            selected.last_part=step

        # No entry exists yet for user for the future self dialog in 
        # the intervention state table
        else:
            selected_user = session.query(Users).filter_by(nicedayuid=user_id).one_or_none()

            # User exists in Users table
            if selected_user is not None:
                entry = UserInterventionState(intervention_component="future_self_dialog",
                                              last_time=last_time, 
                                              last_part=step)
                selected_user.user_intervention_state.append(entry)

            # User does not exist in Users table
            else:
                logging.error("Error: User not in Users table")

        session.commit()  # Update database

        return []
    
    
class ActionGetFirstAidKit(Action):
    """To get the first aid kit from the database."""

    def name(self):
        return "action_get_first_aid_kit"

    async def run(self, dispatcher, tracker, domain):
        
        session = get_db_session(db_url=DATABASE_URL)
        user_id = tracker.current_state()['sender_id']
        
        selected = (
            session.query(
                FirstAidKit
            )
            .filter(
                FirstAidKit.users_nicedayuid==user_id
            )
            .all()
        )
        
        kit_text = ""
        kit_exists = False
        
        if selected is not None:
            
            kit_exists = True
        
            for activity_idx, activity in enumerate(selected):
                kit_text += str(activity_idx + 1) + ") "
                if activity.intervention_activity_id is None:
                    kit_text += activity.user_activity_title
                else:
                    kit_text += activity.intervention_activity.intervention_activity_title
                if not activity_idx == len(selected) - 1:
                    kit_text += "\n"
        
        return [SlotSet("first_aid_kit_text", kit_text),
                SlotSet("first_aid_kit_exists", kit_exists)]


# Set smoked cigarettes tracker reminder
class SetCigarettesTrackerReminder(Action):
    def name(self):
        return "action_set_cigarettes_tracker_reminder"

    async def run(self, dispatcher, tracker, domain):
        client = NicedayClient(NICEDAY_API_ENDPOINT)
        user_id = int(tracker.current_state()['sender_id'])

        recursive_rule = rrule(DAILY, dtstart=datetime.datetime.now().astimezone(TIMEZONE))
        client.set_tracker_reminder(user_id,
                                    definitions.TrackerName.SMOKING.value,
                                    "This is a tracker",
                                    recursive_rule)
        return[]
