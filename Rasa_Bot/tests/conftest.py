from pathlib import Path
import json

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa.shared.core.domain import Domain

import pytest

here = Path(__file__).parent.resolve()
WEEKLY_PLAN_TRACKER = Tracker.from_dict(json.load(open(here / "./data/weekly_plan_tracker.json")))


@pytest.fixture
def dispatcher() -> CollectingDispatcher:
    """Create a clean dispatcher"""
    return CollectingDispatcher()

@pytest.fixture
def domain() -> DomainDict:
    """Load the domain and return it as a dictionary"""
    domain = Domain.load("domain.yml")
    return domain.as_dict()
