"""
Stores definitions used in rasa actions, related to database, endpoints, timezone etcetera.
"""
import os
from dateutil import tz
from enum import Enum


# dev or prod environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# load database url and niceday_api_endpoint variables
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')

# information for reading sensors data
SENSOR_KEY_PATH = '/app/sensorprivatekey'

if ENVIRONMENT == 'prod':
    STEPS_URL = 'https://portal.rrdweb.nl/servlets/r2d2/v6.0.4/project/perfectfit/table' \
                '/garmin_steps_day '
    # TODO: replace with actual url when this will be made available
    INTENSITY_URL = ''
else:
    STEPS_URL = 'https://www.rrdhost.nl/servlets/r2d2/v6.0.4/project/perfectfit/table' \
                '/garmin_steps_day '
    # TODO: replace with actual url when this will be made available
    INTENSITY_URL = ''

TOKEN_HEADER = 'X-PerfectFit-Auth-Token'

# Timezone for saving data to database
TIMEZONE = tz.gettz("Europe/Amsterdam")

RABBITMQ_URL = os.getenv('RABBITMQ_URL')

MORNING = (6, 12)
AFTERNOON = (12, 18)
EVENING = (18, 24)

# Times to start components during times
MORNING_SEND_TIME = 7
AFTERNOON_SEND_TIME = 15
EVENING_SEND_TIME  = 20

# Daypart names in Dutch
DAYPART_NAMES_DUTCH = ["ochtend", "middag", "avond"]

# Confidence slots in profile creation dialog
# Start with the last one, needed for breaking out of confidence slot asking
PROFILE_CREATION_CONF_SLOTS = ["profile_creation_conf_" + str(i) + "_slot" for i in range(10, 0, 
                                                                                          -1)]
# number of activities displayed by the first aid kit
NUM_TOP_ACTIVITIES = 5

# Images for file sharing
FILE_PATH_IMAGE_PA = '/app/hoe_intensief_beweeg_jij.jpg'

### Persuasion in general activity dialog
# Optimal policy based on the one computed in the paper by Albers et al. (2023)
# Opt policy for [want][prompts][need]
# Start at 1, since database values start at 1.
# 1 = commitment, 2 = consensus, 3 = no persuasion
OPT_POLICY = [[[1, 2], [3, 2]],[[1, 1], [3, 1]]]
# Feature means to map features to binary ones
# want, prompts, need 
# (+1 compared to paper, because here values are from 1-5 (not 0-4))
STATE_FEATURE_MEANS = [3.96, 3.74, 3.88]
# Persuasive messages for the persuasion types of commitment and consensus.
# Adapted based on the ones used in the paper by Albers et al. (2022)
# (https://doi.org/10.1371/journal.pone.0277295)
COMMITMENT = ["Vergeet niet: Je hebt besloten om gezonder te gaan leven. "\
                 "Het zal goed voelen wanneer je je aan deze belofte houdt.",
              "Vergeet niet: Je hebt besloten om gezonder te gaan leven. "\
                 "We willen natuurlijk dat je hier niet te veel over nadenkt, "\
                 "maar het zal niet fijn voelen als je je niet aan deze belofte "\
                 "houdt.",
              "Vergeet niet: Je wilt graag gezonder gaan leven. Ik gun je dat "\
                 "dit gaat lukken.",
              "Vergeet niet: Je wilt graag gezonder gaan leven. Ik hoop dat je "\
                 "deze belofte niet breekt.",
              "Vergeet niet: Je hebt beloofd om iemand te worden die gezonder leeft. "\
                 "Deze oefening kan je helpen om deze persoon te worden.",
              "Vergeet niet: Je hebt beloofd om iemand te worden die gezonder leeft. "\
                 "Als je deze oefening NIET doet, kan het moeilijker zijn om "\
                 "deze persoon te worden."]
CONSENSUS = ["De meeste mensen denken dat deze oefening zal helpen om",
             "De meeste mensen denken dat als je deze oefening NIET doet, "\
                 "het moeilijker kan zijn om",
             "Het grootste deel van de mensen gelooft dat deze oefening zal helpen om",
             "Het grootste deel van de mensen gelooft dat als je deze oefening "\
                 "NIET doet, het moeilijker kan zijn om"]
# Reflective questions for persuasion types of commitment and consensus
# Adapted based on the ones used in the paper by Albers et al. (2022)
# (https://doi.org/10.1371/journal.pone.0277295)
REFLECTIVE_QUESTION_COMMITMENT = "Je hebt het besluit genomen om gezonder te "\
   "gaan leven. Hoe helpt deze oefening jou hierbij?"
REFLECTIVE_QUESTION_COMMITMENT_IDENTITY = "Hoe helpt deze oefening jou bij "\
   "jouw besluit om iemand te worden die gezonder leeft?"
REFLECTIVE_QUESTION_CONSENSUS = "Hoe denk je dat deze oefening iemand zoals "\
   "jou kan helpen om gezonder te gaan leven?"

# Accepted misspelled words for days of the weeks
DAYS_OF_WEEK_ACCEPTED = {"maandag": ["maandag", "mandag", "maadag"],
                         "diensdag": ["dinsdag", "diensdag", "diensdah"],
                         "woensdag": ["woensdag", "wonsdag", "wensdag"],
                         "donderdag": ["donderdag", "dondrdag", "dondedag"],
                         "vrijdag": ["vrijdag", "vridag", "vrida", "vrjdag", 
                                     "vijdag"],
                         "zaterdag": ["zaterdag", "zatedag"],
                         "zondag": ["zondag", "zodag", "sondag"]}
# List of days of week in Dutch
DAYS_OF_WEEK = ["maandag", "diensdag", "woensdag", "donderdag", "vrijdag",
                "zaterdag", "zondag"]

activities_categories = {1: 'self-related',
                         2: 'educational',
                         3: 'practical',
                         4: 'reinforcement',
                         5: 'motivational'}

# celery tasks
# trigger an intent immediately
TRIGGER_INTENT = 'celery_tasks.trigger_intent'
# pause the conversation and trigger a new component afterwards
PAUSE_AND_TRIGGER = 'celery_tasks.pause_and_trigger'


class FsmStates:
    ONBOARDING = "Onboarding"
    TRACKING = "Tracking"
    GOALS_SETTING = "Goals setting"
    BUFFER = "Buffer"
    EXECUTION_RUN = "Execution run"
    RELAPSE = "Relapse"
    CLOSING = "Closing"


class DialogQuestions(Enum):
    FUTURE_SELF_SMOKER_WORDS = 1  # Which three words suits you as smoker?
    FUTURE_SELF_SMOKER_WHY = 2  # Why did you pick these words for smoking?
    FUTURE_SELF_MOVER_WORDS = 3  # Which three words suits you as exerciser?
    FUTURE_SELF_MOVER_WHY = 4  # Why did you pick these words for exercising?
    FUTURE_SELF_I_SEE_MYSELF_AS_SMOKER = 5  # I see myself as smoker, non-smoker or quitter
    FUTURE_SELF_I_SEE_MYSELF_AS_MOVER = 6  # I see myself as active, bit active or not active
