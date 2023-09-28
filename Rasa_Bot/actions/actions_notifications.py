import numpy as np
from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from .definitions import REDIS_URL, INACTIVE_THRESHOLD_STEPS
from .helper import get_weekly_intensity_minutes_goal_from_db
import datetime
import logging
from sensorapi.connector import get_daily_step_goal, get_steps_data

celery = Celery(broker=REDIS_URL)


class ActionGetDailyStepGoal(Action):
    def name(self):
        return "action_notifications_get_daily_step_goal"

    async def run(self, dispatcher, tracker, domain):
        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']
        # Get pa daily step goal
        pa_goal = get_daily_step_goal(user_id)
        if pa_goal is None:
            dispatcher.utter_message(response="Er is iets mis met de data. Contact de onderzoeker:"
                                              "perfectfit@lumc.nl")
            logging.error(f"User id: {user_id}, dialog: notification or goal setting,"
                          "action: action_notifications_get_daily_step_goal")
            return [SlotSet("notifications_daily_step_goal", 2000)]

        return [SlotSet("notifications_daily_step_goal", pa_goal)]


class ActionNotificationsGetNumberStepsYesterday(Action):
    def name(self):
        return "action_notifications_get_number_steps_yesterday"

    async def run(self, dispatcher, tracker, domain):
        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']

        # Get right days
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=1)

        steps_data = get_steps_data(user_id, start, end)
        if not steps_data:
            return [SlotSet("notifications_steps_yesterday", 0)]

        steps_yesterday = steps_data[0]['steps']
        return [SlotSet("notifications_steps_yesterday", steps_yesterday)]


class ActionNoticiationsCheckWatchWear(Action):
    def name(self):
        return "action_notifications_check_watch_wear"

    async def run(self, dispatcher, tracker, domain):
        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']

        # Get steps data from last 3 days
        today = datetime.datetime.now()
        start = today - datetime.timedelta(days=3)
        steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=today)

        # Check how many days steps < INACTIVE_THRESHOLD_STEPS
        steps = [day['steps'] for day in steps_data]
        num_days = len(steps_data)
        if num_days == 0:
            dispatcher.utter_message(response="utter_notifications_contact_researcher_no_data")
            return []

        days_insufficient = sum(np.array(steps) < INACTIVE_THRESHOLD_STEPS)
        # Check for last 3 days: if data is missing, or if present <1000
        if num_days == days_insufficient:
            dispatcher.utter_message(response="utter_notifications_contact_researcher_no_data")
            return []

        # Check if yesterday is available in sensor data, or, if present < 1000
        if ((today - datetime.timedelta(days=1)).date() != steps_data[-1]['date']) or \
                steps_data[-1]['steps'] < INACTIVE_THRESHOLD_STEPS:
            dispatcher.utter_message(response="utter_notifications_reminder_wear_watch_1")
            dispatcher.utter_message(response="utter_notifications_reminder_wear_watch_2")
            return []

        return []


class ActionGetWeeklyIntensityMinutesFromDb(Action):
    def name(self):
        return "action_notifications_weekly_intensity_minutes_from_db"

    async def run(self, dispatcher, tracker, domain):
        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']

        # Get pa daily step goal
        pa_goal = get_weekly_intensity_minutes_goal_from_db(user_id)

        return [SlotSet("notifications_pa_intensity_goal", pa_goal)]


class ActionPauseOneMinute(Action):
    def name(self):
        return "pause_one_minute"

    async def run(self, dispatcher, tracker, domain):
        # Get sender ID from slot, this is a string
        user_id = tracker.current_state()['sender_id']

        time = datetime.datetime.now() + datetime.timedelta(seconds=60)
        celery.send_task('celery_tasks.pause_and_resume',
                         (user_id, time, False))

        return []
