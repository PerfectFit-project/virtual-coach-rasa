from pathlib import Path
import json
from rasa_sdk import Tracker

here = Path(__file__).parent.resolve()

WEEKLY_PLAN_TRACKER = Tracker.from_dict(json.load(open(here / "./data/weekly_plan_tracker.json")))