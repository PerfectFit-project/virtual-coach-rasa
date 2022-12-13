"""
Stores definitions used in rasa actions, related to database, endpoints, timezone etcetera.
"""
import os
from enum import Enum

from dateutil import tz

# load database url and niceday_api_endopint variables
DATABASE_URL = os.getenv('DATABASE_URL')
NICEDAY_API_ENDPOINT = os.getenv('NICEDAY_API_ENDPOINT')

# Timezone for saving data to database
TIMEZONE = tz.gettz("Europe/Amsterdam")

REDIS_URL = os.getenv('REDIS_URL')

MORNING = (6, 12)
AFTERNOON = (12, 18)
EVENING = (18, 24)

# number of activities displayed by the first aid kit
NUM_TOP_ACTIVITIES = 5

# Opt policy for [want][prompts][need]
OPT_POLICY = [[[0, 1], [2, 1]],[[0, 0], [2, 0]]]
# Feature means to map features to binary ones
STATE_FEATURE_MEANS = [3.96, 3.74, 3.88]  # want, prompts, need (+1 compared to paper, because here values are from 1-5 (not 0-4))
# Persuasive messages for the persuasion types of commitment and consensus
COMMITMENT = ["Remember: You have decided to quit smoking. You will feel good if you keep your promise to yourself.",
              "Remember: You have decided to quit smoking. You will feel bad if you break your promise to yourself.",
              "Remember: You've committed to quit smoking. I hope you'll be sticking to it.",
              "Remember: You've committed to quit smoking. I hope you'll not break your commitment.",
              "Remember: You've committed to become somebody who has quit smoking. Doing this activity may help you to become this person.",
              "Remember: You've decided to become somebody who has quit smoking. If you do NOT do this activity, it may be more difficult to become this person."]
CONSENSUS = ["Most people think that doing this activity may help",
             "Most people believe that NOT doing this activity may make it more difficult",
             "The majority of people believe that doing this activity may help",
             "The majority of people think that NOT doing this activity may make it more difficult"]

class DialogQuestions(Enum):
    FUTURE_SELF_SMOKER_WORDS = 1  # Which three words suits you as smoker?
    FUTURE_SELF_SMOKER_WHY = 2  # Why did you pick these words for smoking?
    FUTURE_SELF_MOVER_WORDS = 3  # Which three words suits you as exerciser?
    FUTURE_SELF_MOVER_WHY = 4  # Why did you pick these words for exercising?
    FUTURE_SELF_I_SEE_MYSELF_AS_SMOKER = 5  # I see myself as smoker, non-smoker or quitter
    FUTURE_SELF_I_SEE_MYSELF_AS_MOVER = 6  # I see myself as active, bit active or not active
