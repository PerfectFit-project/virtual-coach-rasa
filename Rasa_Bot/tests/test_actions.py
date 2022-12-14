"""Unit tests for the custom actions"""
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from contextlib import contextmanager
from typing import Text, Union
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.interfaces import Tracker
from Rasa_Bot.actions.actions_general_activity import (
    get_user_intervention_activity_inputs,
    CheckIfFirstExecutionGA,
    GetActivityUserInput,
    CheckUserInputRequired,
    CheckActivityDone,
    SaveDescriptionInDb,
    SetSlotGeneralActivity,
    GeneralActivityCheckRating,
    get_random_activities,
    GetThreeRandomActivities,
    GetLastPerformedActivity,
    LoadActivity,
)

from Rasa_Bot.actions.actions_future_self_dialog import (
    ValidateWhyPickedMoverWordsForm,
)
from Rasa_Bot.actions.actions_minimum_functional_product import SavePlanWeekCalendar

from Rasa_Bot.tests.conftest import EMPTY_TRACKER
from virtual_coach_db.dbschema.models import InterventionActivitiesPerformed, InterventionActivity, FirstAidKit
from sqlalchemy import update
from virtual_coach_db.helper import ExecutionInterventionComponents
from Rasa_Bot.actions.definitions import NUM_TOP_ACTIVITIES


@pytest.fixture
def tracker() -> Tracker:
    yield EMPTY_TRACKER


def new_mocker_filter(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock(return_value=mocker.MagicMock(
        **{"limit": mocker.MagicMock(**{"all": mocker.MagicMock()})}))


@pytest.fixture
def mocker_db_session(mocker: MockerFixture) -> MagicMock:
    mocker_get_db_session = mocker.patch(
        "Rasa_Bot.actions.actions_general_activity.get_db_session")
    mocker_db_session = mocker.MagicMock(
        **{
            "query": mocker.MagicMock(
                return_value=mocker.MagicMock(
                    **{
                        "filter": new_mocker_filter(mocker),
                        "order_by": mocker.MagicMock(
                            return_value=mocker.MagicMock(**{"filter": new_mocker_filter(mocker)})
                        ),
                    }
                )
            ),
            "execute": mocker.MagicMock(),
            "commit": mocker.MagicMock(),
            "add": mocker.MagicMock(),
        }
    )
    mocker_get_db_session.return_value = mocker_db_session
    yield mocker_db_session


@pytest.fixture
def mocker_get_user_intervention_activity_inputs(
        mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "Rasa_Bot.actions.actions_general_activity.get_user_intervention_activity_inputs")


def test_get_user_intervention_activity_inputs(
    mocker: MockerFixture, tracker: Tracker, mocker_db_session: MagicMock
) -> None:
    user_id = 3
    last_activity_id_slot = 2
    inputs = get_user_intervention_activity_inputs(
        user_id, last_activity_id_slot)
    mocker_db_session.query.assert_called_once_with(
        InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == user_id)
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot)


@pytest.mark.asyncio
async def test_run_action_check_if_first_execution_ga__first_time(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckIfFirstExecutionGA()

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[])
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(
        InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"])

    expected_events = [SlotSet("general_activity_first_execution", True)]
    assert expected_events == events


@pytest.mark.asyncio
async def test_run_action_check_if_first_execution_ga__not_first_time(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckIfFirstExecutionGA()

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[InterventionActivitiesPerformed()])
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(
        InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"])

    assert events == [SlotSet("general_activity_first_execution", False)]


@pytest.mark.asyncio
async def test_run_action_get_activity_user_input(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_get_user_intervention_activity_inputs: MagicMock,
) -> None:
    action = GetActivityUserInput()

    last_activity_id_slot = 11
    tracker.add_slots(
        [SlotSet("last_activity_id_slot", last_activity_id_slot)])
    mocker_get_user_intervention_activity_inputs.return_value = [
        InterventionActivitiesPerformed(user_input="user_input1"),
        InterventionActivitiesPerformed(user_input="user_input2"),
    ]

    events = await action.run(dispatcher, tracker, domain)

    mocker_get_user_intervention_activity_inputs.assert_called_once_with(
        tracker.current_state()["sender_id"], last_activity_id_slot
    )
    assert events == [SlotSet("activity_user_input", "user_input2")]


@pytest.mark.asyncio
async def test_run_action_check_user_input_required__required(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckUserInputRequired()

    last_activity_id_slot = 11
    tracker.add_slots(
        [SlotSet("last_activity_id_slot", last_activity_id_slot)])
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivity(
                user_input_required=False), InterventionActivity(
                user_input_required=True), ])
    events = await action.run(dispatcher, tracker, domain)
    mocker_db_session.query.assert_called_once_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id == last_activity_id_slot)

    assert events == [SlotSet("is_user_input_required", False)]


@pytest.mark.asyncio
async def test_run_action_check_user_input_required__not_required(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckUserInputRequired()

    last_activity_id_slot = 11
    tracker.add_slots(
        [SlotSet("last_activity_id_slot", last_activity_id_slot)])
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivity(
                user_input_required=True), InterventionActivity(
                user_input_required=True), ])
    events = await action.run(dispatcher, tracker, domain)
    mocker_db_session.query.assert_called_once_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id == last_activity_id_slot)

    assert events == [SlotSet("is_user_input_required", True)]


@pytest.mark.asyncio
async def test_run_action_check_activity_done__not_done(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_get_user_intervention_activity_inputs: MagicMock,
) -> None:
    action = CheckActivityDone()

    mocker_get_user_intervention_activity_inputs.return_value = [
        InterventionActivitiesPerformed(user_input="user_input1"),
        InterventionActivitiesPerformed(user_input=None),
    ]
    last_activity_id_slot = 11
    tracker.add_slots(
        [SlotSet("last_activity_id_slot", last_activity_id_slot)])
    events = await action.run(dispatcher, tracker, domain)
    mocker_get_user_intervention_activity_inputs.assert_called_once_with(
        tracker.current_state()["sender_id"], last_activity_id_slot
    )

    assert events == [SlotSet("is_activity_done", False)]


@pytest.mark.asyncio
async def test_run_action_check_activity_done__done(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = CheckActivityDone()

    last_activity_id_slot = 11
    tracker.add_slots(
        [SlotSet("last_activity_id_slot", last_activity_id_slot)])
    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[
            InterventionActivitiesPerformed(
                user_input="user_input1"), InterventionActivitiesPerformed(
                user_input="user_input2"), ])
    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_once_with(
        InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"])
    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        InterventionActivitiesPerformed.intervention_activity_id == last_activity_id_slot)

    assert events == [SlotSet("is_activity_done", True)]


@pytest.mark.asyncio
async def test_run_action_save_description_in_db(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
    mocker_get_user_intervention_activity_inputs: MagicMock,
) -> None:
    action = SaveDescriptionInDb()

    description = "This is a description"
    last_activity_id_slot = 11
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
            SlotSet("general_activity_description_slot", description),
        ]
    )

    mocker_get_user_intervention_activity_inputs.return_value = [
        InterventionActivitiesPerformed(intervention_activities_performed_id=1),
        InterventionActivitiesPerformed(intervention_activities_performed_id=2),
    ]

    events = await action.run(dispatcher, tracker, domain)
    mocker_get_user_intervention_activity_inputs.assert_called_once_with(
        tracker.current_state()["sender_id"], last_activity_id_slot
    )

    statement = (
        update(InterventionActivitiesPerformed)
        .where(InterventionActivitiesPerformed.intervention_activities_performed_id == 2)
        .values(user_input=description)
    )
    mocker_db_session.execute.assert_called_once()
    mocker_db_session.execute.call_args.args[0].compare(statement)
    mocker_db_session.commit.assert_called_once()
    assert events == []


@pytest.mark.asyncio
async def test_run_action_set_slot_general_activity(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = SetSlotGeneralActivity()

    events = await action.run(dispatcher, tracker, domain)
    assert events == [
        SlotSet(
            "current_intervention_component",
            ExecutionInterventionComponents.GENERAL_ACTIVITY)]


@pytest.mark.asyncio
async def test_run_action_general_activity_check_rating__has_record_and_low(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GeneralActivityCheckRating()

    last_activity_id_slot = 2
    activity_useful_rating = 3.0
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
            SlotSet("activity_useful_rating", activity_useful_rating),
        ]
    )

    top_n_activities = [
        FirstAidKit(activity_rating=8),
        FirstAidKit(activity_rating=7),
        FirstAidKit(activity_rating=6),
        FirstAidKit(activity_rating=5),
        FirstAidKit(activity_rating=4),
    ]
    current_record = [FirstAidKit(first_aid_kit_id=3)]
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all = (
        mocker.MagicMock(return_value=top_n_activities))

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=current_record)
    assert len(top_n_activities) <= NUM_TOP_ACTIVITIES

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.order_by.assert_called_once()
    mocker_db_session.query.return_value.order_by.call_args.args[0].compare(
        FirstAidKit.activity_rating.desc())
    mocker_db_session.query.return_value.order_by.return_value.filter.assert_called_once()
    mocker_db_session.query.return_value.order_by.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.assert_called_once_with(
        NUM_TOP_ACTIVITIES)
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])

    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        FirstAidKit.intervention_activity_id == last_activity_id_slot)
    statement = (
        update(FirstAidKit)
        .where(FirstAidKit.first_aid_kit_id == current_record[0].first_aid_kit_id)
        .values(activity_rating=activity_useful_rating)
    )
    mocker_db_session.execute.assert_called_once()
    mocker_db_session.execute.call_args.args[0].compare(statement)
    mocker_db_session.commit.assert_called_once()
    assert events == [SlotSet("general_activity_low_high_rating", "low")]


@pytest.mark.asyncio
async def test_run_action_general_activity_check_rating__has_record_and_high(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GeneralActivityCheckRating()

    last_activity_id_slot = 2
    activity_useful_rating = 5.0
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
            SlotSet("activity_useful_rating", activity_useful_rating),
        ]
    )

    top_n_activities = [
        FirstAidKit(activity_rating=8),
        FirstAidKit(activity_rating=7),
        FirstAidKit(activity_rating=6),
        FirstAidKit(activity_rating=5),
        FirstAidKit(activity_rating=4),
    ]
    current_record = [FirstAidKit(first_aid_kit_id=3)]
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all = (
        mocker.MagicMock(return_value=top_n_activities))

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=current_record)
    assert len(top_n_activities) <= NUM_TOP_ACTIVITIES

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.order_by.assert_called_once()
    mocker_db_session.query.return_value.order_by.call_args.args[0].compare(
        FirstAidKit.activity_rating.desc())
    mocker_db_session.query.return_value.order_by.return_value.filter.assert_called_once()
    mocker_db_session.query.return_value.order_by.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.assert_called_once_with(
        NUM_TOP_ACTIVITIES)
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])

    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        FirstAidKit.intervention_activity_id == last_activity_id_slot)
    statement = (
        update(FirstAidKit)
        .where(FirstAidKit.first_aid_kit_id == current_record[0].first_aid_kit_id)
        .values(activity_rating=activity_useful_rating)
    )
    mocker_db_session.execute.assert_called_once()
    mocker_db_session.execute.call_args.args[0].compare(statement)
    mocker_db_session.commit.assert_called_once()
    assert events == [SlotSet("general_activity_low_high_rating", "high")]


@pytest.mark.asyncio
async def test_run_action_general_activity_check_rating__no_record(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GeneralActivityCheckRating()

    last_activity_id_slot = 2
    activity_useful_rating = 5.0
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
            SlotSet("activity_useful_rating", activity_useful_rating),
        ]
    )

    top_n_activities = [
        FirstAidKit(activity_rating=8),
        FirstAidKit(activity_rating=7),
        FirstAidKit(activity_rating=6),
        FirstAidKit(activity_rating=5),
        FirstAidKit(activity_rating=4),
    ]
    current_record = []
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all = (
        mocker.MagicMock(return_value=top_n_activities))

    mocker_db_session.query.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=current_record)
    assert len(top_n_activities) <= NUM_TOP_ACTIVITIES

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.order_by.assert_called_once()
    mocker_db_session.query.return_value.order_by.call_args.args[0].compare(
        FirstAidKit.activity_rating.desc())
    mocker_db_session.query.return_value.order_by.return_value.filter.assert_called_once()
    mocker_db_session.query.return_value.order_by.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.assert_called_once_with(
        NUM_TOP_ACTIVITIES)
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.assert_called_once()

    mocker_db_session.query.assert_called_with(FirstAidKit)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        FirstAidKit.users_nicedayuid == tracker.current_state()["sender_id"])

    assert mocker_db_session.query.return_value.filter.call_args.args[1].compare(
        FirstAidKit.intervention_activity_id == last_activity_id_slot)

    mocker_db_session.add.assert_called_once()
    assert mocker_db_session.add.call_args.args[0].users_nicedayuid == tracker.current_state()[
        "sender_id"]
    assert mocker_db_session.add.call_args.args[0].intervention_activity_id == last_activity_id_slot
    assert mocker_db_session.add.call_args.args[0].activity_rating == int(
        activity_useful_rating)

    mocker_db_session.commit.assert_called()
    mocker_db_session.execute.assert_not_called()
    assert events == [SlotSet("general_activity_low_high_rating", "high")]


def test_get_random_activities(
        mocker: MockerFixture,
        mocker_db_session: MagicMock) -> None:
    avoid_activity_id = 1
    number_of_activities = 3

    mocker_db_session.query.return_value.filter.return_value.all.return_value = [
        InterventionActivity(
            intervention_activity_id=2), InterventionActivity(
            intervention_activity_id=3), InterventionActivity(
                intervention_activity_id=4), InterventionActivity(
                    intervention_activity_id=5), InterventionActivity(
                        intervention_activity_id=6), ]
    random_activities = get_random_activities(
        avoid_activity_id, number_of_activities)

    mocker_db_session.query.assert_called_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id != avoid_activity_id)
    mocker_db_session.query.return_value.filter.return_value.all.assert_called_once()
    assert len(random_activities) == number_of_activities
    visited = set()
    for random_activity in random_activities:
        assert random_activity not in visited
        assert random_activity.intervention_activity_id != avoid_activity_id
        visited.add(random_activity)


@pytest.mark.asyncio
async def test_run_action_get_three_random_activities(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GetThreeRandomActivities()
    last_activity_id_slot = 1
    activity_useful_rating = 5.0
    tracker.add_slots(
        [
            SlotSet("last_activity_id_slot", last_activity_id_slot),
        ]
    )
    random_three_activities = [
        InterventionActivity(intervention_activity_id=2),
        InterventionActivity(intervention_activity_id=3),
        InterventionActivity(intervention_activity_id=4),
    ]
    mocker_get_random_activities = mocker.patch(
        "Rasa_Bot.actions.actions_general_activity.get_random_activities")
    mocker_get_random_activities.return_value = random_three_activities

    events = await action.run(dispatcher, tracker, domain)

    mocker_get_random_activities.assert_called_once_with(
        last_activity_id_slot, 3)
    assert events == [
        SlotSet(
            "activity1_name", random_three_activities[0].intervention_activity_title), SlotSet(
            "activity2_name", random_three_activities[1].intervention_activity_title), SlotSet(
                "activity3_name", random_three_activities[2].intervention_activity_title), SlotSet(
                    "rnd_activities_ids", [
                        activity.intervention_activity_id for activity in random_three_activities]), ]


@pytest.mark.asyncio
async def test_run_action_get_last_performed_activity__no_last(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GetLastPerformedActivity()
    last_activity_title = "title"
    intervention_activity_id = 3
    last_activity = InterventionActivity(
        intervention_activity_title=last_activity_title,
        intervention_activity_id=intervention_activity_id)
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=[InterventionActivitiesPerformed(intervention_activity=last_activity)])

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.order_by.assert_called_once()
    assert mocker_db_session.query.return_value.order_by.called_args.args[0].compare(
        InterventionActivitiesPerformed.completed_datetime.desc())
    mocker_db_session.query.return_value.order_by.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.order_by.return_value.filter.called_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"])
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.all.assert_called_once_with()

    assert events == [
        SlotSet("last_activity_slot", last_activity_title),
        SlotSet("last_activity_id_slot", intervention_activity_id),
    ]


@pytest.mark.asyncio
async def test_run_action_get_last_performed_activity__has_last(
    mocker: MockerFixture,
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
) -> None:
    action = GetLastPerformedActivity()

    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.all = mocker.MagicMock(
        return_value=None)

    events = await action.run(dispatcher, tracker, domain)

    mocker_db_session.query.assert_called_with(InterventionActivitiesPerformed)
    mocker_db_session.query.return_value.order_by.assert_called_once()
    assert mocker_db_session.query.return_value.order_by.called_args.args[0].compare(
        InterventionActivitiesPerformed.completed_datetime.desc())
    mocker_db_session.query.return_value.order_by.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.order_by.return_value.filter.called_args.args[0].compare(
        InterventionActivitiesPerformed.users_nicedayuid == tracker.current_state()["sender_id"])
    mocker_db_session.query.return_value.order_by.return_value.filter.return_value.all.assert_called_once_with()

    assert events == [
        SlotSet(
            "last_activity_slot", None), SlotSet(
            "last_activity_id_slot", None)]


@pytest.mark.asyncio
async def test_run_action_load_activity__no_inputs(
    mocker: MockerFixture,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
    mocker_get_user_intervention_activity_inputs: MagicMock,
) -> None:
    action = LoadActivity()
    dispatcher = mocker.MagicMock(utter_message=mocker.MagicMock())

    tracker.add_slots([SlotSet("general_activity_next_activity_slot", "2"), SlotSet(
        "rnd_activities_ids", [1, 5, 3])])

    mocker_get_user_intervention_activity_inputs.return_value = None
    mocker_db_session.query.return_value.filter.return_value.all.return_value = [
        InterventionActivity(intervention_activity_full_instructions="intruction1"),
        InterventionActivity(intervention_activity_full_instructions="intruction2"),
    ]

    events = await action.run(dispatcher, tracker, domain)

    mocker_get_user_intervention_activity_inputs.assert_called_once_with(
        tracker.current_state()["sender_id"], 5)
    mocker_db_session.add.assert_called_once()

    assert mocker_db_session.add.call_args.args[0].users_nicedayuid == tracker.current_state()[
        "sender_id"]
    assert mocker_db_session.add.call_args.args[0].intervention_activity_id == 5
    assert mocker_db_session.add.call_args.args[0].user_input is None

    mocker_db_session.commit.assert_called_once()

    mocker_db_session.query.assert_called_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()
    assert mocker_db_session.query.return_value.filter.called_args.args[0].compare(
        InterventionActivity.intervention_activity_id == 5)
    mocker_db_session.query.return_value.filter.return_value.all.assert_called_once()
    dispatcher.utter_message.assert_called_once_with(text="intruction1")
    assert events == []


@pytest.mark.asyncio
async def test_run_action_load_activity__has_inputs(
    mocker: MockerFixture,
    tracker: Tracker,
    domain: DomainDict,
    mocker_db_session: MagicMock,
    mocker_get_user_intervention_activity_inputs: MagicMock,
) -> None:
    action = LoadActivity()
    dispatcher = mocker.MagicMock(utter_message=mocker.MagicMock())

    tracker.add_slots([SlotSet("general_activity_next_activity_slot", "2"), SlotSet(
        "rnd_activities_ids", [1, 5, 3])])

    mocker_get_user_intervention_activity_inputs.return_value = [
        InterventionActivitiesPerformed(user_input="input1"),
        InterventionActivitiesPerformed(user_input="input2"),
    ]
    mocker_db_session.query.return_value.filter.return_value.all.return_value = [
        InterventionActivity(intervention_activity_full_instructions="intruction1"),
        InterventionActivity(intervention_activity_full_instructions="intruction2"),
    ]

    events = await action.run(dispatcher, tracker, domain)

    mocker_get_user_intervention_activity_inputs.assert_called_once_with(
        tracker.current_state()["sender_id"], 5)
    mocker_db_session.add.assert_called_once()

    assert mocker_db_session.add.call_args.args[0].users_nicedayuid == tracker.current_state()[
        "sender_id"]
    assert mocker_db_session.add.call_args.args[0].intervention_activity_id == 5
    assert mocker_db_session.add.call_args.args[0].user_input == "input2"

    mocker_db_session.commit.assert_called_once()

    mocker_db_session.query.assert_called_with(InterventionActivity)
    mocker_db_session.query.return_value.filter.assert_called_once()

    assert mocker_db_session.query.return_value.filter.call_args.args[0].compare(
        InterventionActivity.intervention_activity_id == 5)
    mocker_db_session.query.return_value.filter.return_value.all.assert_called_once()
    dispatcher.utter_message.assert_called_once_with(text="intruction1")
    assert events == []


# TODO: If this is a recurring pattern, this can be turned into a fixture
@contextmanager
def latest_message(tracker, message):
    # this is not thread safe
    original = tracker.latest_message["text"]
    tracker.latest_message["text"] = message
    yield tracker
    tracker.latest_message["text"] = original


has_enough_words_examples = (
    ("too few", None),
    (
        "User provided enough words to analyze their response.",
        "User provided enough words to analyze their response.",
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response,expected",
    has_enough_words_examples,
    ids=("negative", "positive"),
)
async def test_run_action_validate_why_picked_mover_words_form(
    dispatcher: CollectingDispatcher,
    domain: DomainDict,
    response: Text,
    expected: Union[Text, None],
):
    with latest_message(EMPTY_TRACKER, response) as tracker:
        action = ValidateWhyPickedMoverWordsForm()
        slots = action.validate_why_picked_words(
            response,
            dispatcher,
            tracker,
            domain,
        )
        expected_slots = {"why_picked_words": expected}

        assert slots == expected_slots
