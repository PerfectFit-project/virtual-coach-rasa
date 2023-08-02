import os
from dateutil import tz

# maximum duration of the dialog in seconds
MAXIMUM_DIALOG_DURATION = 90*60
# maximum number of days of inactivity before sending a notification
MAXIMUM_INACTIVE_DAYS = 10

# time interval in seconds for checking for new connection requests
INVITES_CHECK_INTERVAL = 10*60

# next message is delivered
WORDS_PER_SECOND = 5
# maximum delay, in seconds, between a message and the next one
MAX_DELAY = 10

# PA groups
LOW_PA_GROUP = 1
HIGH_PA_GROUP = 2

# duration in weeks
EXECUTION_DURATION_WEEKS = 12

# intervention times (days)
ACTIVITY_C2_9_DAY_TRIGGER = 6
FUTURE_SELF_INTRO = 8
GOAL_SETTING = 9
# number of days after the weekly reflection for the PA notification to be sent
TIME_DELTA_PA_NOTIFICATION = 4
TRACKING_DURATION = 10
PREPARATION_GA = 14
MAX_PREPARATION_DURATION = 21
EXECUTION_DURATION = EXECUTION_DURATION_WEEKS * 7  # 12 weeks
#

REDIS_URL = os.getenv('REDIS_URL')
ENVIRONMENT = os.getenv('ENVIRONMENT')
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
PAUSE_AND_TRIGGER = 'celery_tasks.pause_and_trigger'
SCHEDULE_TRIGGER_COMPONENT = 'celery_tasks.trigger_scheduled_intervention_component'
TRIGGER_INTENT = 'celery_tasks.trigger_intent'
TIMEZONE = tz.gettz("Europe/Amsterdam")

# dialog states definitions
NOT_RUNNING = 0
RUNNING = 1
EXPIRED = 2
NOTIFY = 3

# definitions of morning hours
MORNING_TIME = 8
