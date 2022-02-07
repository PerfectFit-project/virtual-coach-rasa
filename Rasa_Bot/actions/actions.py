# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
import datetime
import logging
import os
from typing import Any, Dict, Text

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from paalgorithms import weekly_kilometers
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from virtual_coach_db.dbschema.models import Users
from virtual_coach_db.dbschema.models import ClosedUserAnswers
from virtual_coach_db.helper.helper import get_db_session

# load .env-file and get db_host variable
load_dotenv()
DB_HOST = os.getenv('DB_HOST')


# Get the user's age from the database.
# Save the extracted age to a slot.
class GetAgeFromDatabase(Action):
    def name(self):
        return "action_get_age_from_database"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()['sender_id']

        # Create session object to connect db
        session = get_db_session(db_host=DB_HOST)

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
        session = get_db_session(db_host=DB_HOST)

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

# Get weekly plan
class GetMakeda(Action):
    def name(self):
        return "action_get_meee"

    async def run(self, dispatcher, tracker, domain):

        input = tracker.get_slot("input")

        # Calculates weekly kilometers based on age
        len_input = len(input)

        return [SlotSet(len_input)]


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
            dispatcher.utter_message("Kun je een geheel getal tussen 1 en 5 opgeven?")
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
            dispatcher.utter_message("Fijn om te horen dat het goed ging!")
        else:
            dispatcher.utter_message("Jammer, probeer nu goed uit te rusten, "
                                     "dan gaat het de volgende keer vast beter!")
        return []


class ActionStorePaEvaluation(Action):
    """"To save user input from PA evaluation form to database"""

    def name(self):
        return "action_store_pa_evaluation"

    async def run(self, dispatcher, tracker, domain):

        pa_evaluation_response = tracker.get_slot("pa_evaluation_response")
        session = get_db_session()  # Creat session object to connect db

        user_id = tracker.current_state()['sender_id']
        selected = session.query(Users).filter_by(nicedayuid=user_id).one()

        entry = ClosedUserAnswers(value=pa_evaluation_response,
                                  question='paevaluation',
                                  datetime=datetime.datetime.now())
        selected.closed_user_answers.append(entry)
        session.commit()  # Update database
        return [SlotSet("pa_evaluation_response", None)]


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
    if value == 'ja':
        return True
    if value in ['nee', "nee."]:
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
            dispatcher.utter_message("Geef alsjeblieft antwoord met 'ja' of 'nee'?")

        return {"confirm_words_response": yes_or_no_response}
