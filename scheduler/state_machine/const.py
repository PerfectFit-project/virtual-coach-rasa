import os
from dateutil import tz

# intervention times (days)
FUTURE_SELF_INTRO = 8
GOAL_SETTING = 9
TRACKING_DURATION = 10
PREPARATION_GA = 14
MAX_PREPARATION_DURATION = 21
EXECUTION_DURATION = 12 * 7  # 12 weeks
#

REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
TRIGGER_COMPONENT = 'celery_tasks.trigger_intervention_component'
TIMEZONE = tz.gettz("Europe/Amsterdam")