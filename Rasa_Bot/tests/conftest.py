import json
from pathlib import Path

import pytest
from rasa.shared.core.domain import Domain
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

here = Path(__file__).parent.resolve()

# We load an empty conversation tracker. We need a tracker to call
# custom actions in the custom action unit tests.
with open(here / "./data/initial_tracker.json", "r", encoding='utf-8') as f:
    EMPTY_TRACKER = Tracker.from_dict(json.load(f))


@pytest.fixture
def dispatcher() -> CollectingDispatcher:
    """Create a clean dispatcher"""
    return CollectingDispatcher()


@pytest.fixture
def domain() -> DomainDict:
    """Load the domain and return it as a dictionary"""
    domain = Domain.from_directory("Rasa_Bot/domain/")
    return domain.as_dict()
