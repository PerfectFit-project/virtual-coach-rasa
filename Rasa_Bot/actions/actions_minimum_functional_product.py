"""
Contains custom actions for dialogs implemented as part of the 'Minimum Functional Product'
"""
import datetime
import logging
from typing import Any, Dict, Text

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from niceday_client import NicedayClient, definitions
from paalgorithms import weekly_kilometers
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from virtual_coach_db.dbschema.models import (Users, ClosedUserAnswers)
from virtual_coach_db.helper.helper_functions import get_db_session

from .definitions import TIMEZONE, DATABASE_URL, NICEDAY_API_ENDPOINT


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
        return []


# Save weekly plan in calendar
class SavePlanWeekCalendar(Action):
    def name(self):
        return "action_save_plan_week_calendar"

    async def run(self, dispatcher, tracker, domain):
        success = True

        return [SlotSet("success_save_calendar_plan_week", success)]


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
