from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from .definitions import RABBITMQ_URL
from .helper import get_daily_step_goal_from_db, get_weekly_intensity_minutes_goal_from_db
import datetime

celery = Celery(broker=RABBITMQ_URL)

class ActionGetDailyStepGoalFromDb(Action):
    def name(self):
        return "action_notifications_get_daily_step_goal_from_db"

    async def run(self, dispatcher, tracker, domain):
        # Get pa daily step goal
        pa_goal = get_daily_step_goal_from_db()

        return [SlotSet("notifications_daily_step_goal", pa_goal)]


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
