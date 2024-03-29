import random
from sqlalchemy import update
from virtual_coach_db.dbschema.models import (InterventionActivitiesPerformed,
                                              FirstAidKit,
                                              InterventionActivity)
from virtual_coach_db.helper import (Components,
                                     DialogQuestionsEnum)
from virtual_coach_db.helper.helper_functions import get_db_session
from . import validator
from .definitions import (activities_categories, COMMITMENT, CONSENSUS,
                          NUM_TOP_ACTIVITIES,
                          OPT_POLICY, STATE_FEATURE_MEANS,
                          REFLECTIVE_QUESTION_COMMITMENT,
                          REFLECTIVE_QUESTION_COMMITMENT_IDENTITY,
                          REFLECTIVE_QUESTION_CONSENSUS,
                          REDIS_URL)
from .helper import (get_latest_bot_utterance,
                     get_possible_activities,
                     get_user_intervention_activity_inputs,
                     store_dialog_closed_answer_to_db)
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import Any, Dict, Text

from celery import Celery

celery = Celery(broker=REDIS_URL)


# Trigger relapse phase through celery
class TriggerGeneralActivity(Action):
    def name(self):
        return "action_trigger_general_activity"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        celery.send_task('celery_tasks.user_trigger_dialog',
                         (user_id, Components.GENERAL_ACTIVITY))

        return []


class LaunchGaRescheduling(Action):
    """Launch the general activity rescheduling dialog"""

    def name(self):
        return "launch_ga_rescheduling"

    async def run(self, dispatcher, tracker, domain):
        return [FollowupAction('utter_intro_reschedule_ga')]


class GoToCheckActivityDone(Action):
    def name(self):
        return "go_to_check_activity_done"

    async def run(self, dispatcher, tracker, domain):
        return [FollowupAction('check_activity_done')]


class GoToCheckInputRequired(Action):
    def name(self):
        return "go_to_check_input_required"

    async def run(self, dispatcher, tracker, domain):
        return [FollowupAction('check_user_input_required')]


class GoToChooseActivity(Action):
    def name(self):
        return "go_to_choose_activity"

    async def run(self, dispatcher, tracker, domain):
        return [FollowupAction('check_who_decides')]


class GoToRating(Action):
    def name(self):
        return "go_to_rating"

    async def run(self, dispatcher, tracker, domain):
        return [FollowupAction('general_activity_check_rating')]


class CheckIfFirstExecutionGA(Action):
    """Check if it is the first execution"""

    def name(self):
        return "check_if_first_execution_ga"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']
        session = get_db_session()

        performed_activity = (
            session.query(
                InterventionActivitiesPerformed
            )
            .filter(
                InterventionActivitiesPerformed.users_nicedayuid == user_id
            )
            .all()
        )

        # if the query result is empty, no activity has been performed yet
        first_execution = not bool(performed_activity)

        session.close()

        return [SlotSet("general_activity_first_execution", first_execution)]


class GeneralActivityCheckRating(Action):
    """Check if the activity rating is in top five or not"""

    def name(self):
        return "general_activity_check_rating"

    async def run(self, dispatcher, tracker, domain):

        rating_value = int(tracker.get_slot('activity_useful_rating'))
        activity_id = int(tracker.get_slot('last_activity_id_slot'))

        session = get_db_session()
        user_id = tracker.current_state()['sender_id']

        # get the highest scored activities
        top_five_activities = (
            session.query(
                FirstAidKit
            ).order_by(FirstAidKit.activity_rating.desc())
            .filter(
                FirstAidKit.users_nicedayuid == user_id
            )
            .limit(NUM_TOP_ACTIVITIES).all()
        )

        current_record = (
            session.query(
                FirstAidKit
            )
            .filter(
                FirstAidKit.users_nicedayuid == user_id,
                FirstAidKit.intervention_activity_id == activity_id
            )
            .one_or_none()
        )

        if len(top_five_activities) > 0:
            lowest_score = top_five_activities[-1].activity_rating
        else:
            lowest_score = 0

        # if the activity is not in the FAK, add it
        if not current_record:
            save_activity_to_fak(user_id, activity_id, rating_value)

            session.commit()
        else:
            # update the row containing the activity with the new rating
            session.execute(
                update(FirstAidKit)
                .where(FirstAidKit.first_aid_kit_id == current_record.first_aid_kit_id)
                .values(activity_rating=rating_value)
            )

            session.commit()

        session.close()

        if rating_value > lowest_score:
            return [SlotSet("general_activity_low_high_rating", 'high')]

        return [SlotSet("general_activity_low_high_rating", 'low')]


class GetActivityUserInput(Action):
    """Get the user input and save it in the slot"""

    def name(self):
        return "get_activity_user_input"

    async def run(self, dispatcher, tracker, domain):
        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)
        last_input = user_inputs[-1].user_input

        return [SlotSet("activity_user_input", last_input)]


class GetGeneralActivitiesOptions(Action):
    """Get the options for the activities to be presented to the user"""

    def name(self):
        return "get_general_activities_options"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        activity_type_slot = tracker.get_slot('general_activity_activity_type_slot')
        activity_id = tracker.get_slot('last_activity_id_slot')

        activity_type = activities_categories[int(activity_type_slot)]

        _, available = get_possible_activities(user_id,
                                                       activity_type,
                                                       activity_id)

        available_activities_ids = [activity.intervention_activity_id for activity in available]

        options = ["Typ " + str(i + 1) + " als je '" +
                   available[i].intervention_activity_title +
                   "' wilt doen.\n"
                   for i in range(len(available))]

        sentence = str().join(options)

        sentence += "Typ " + \
                    str(len(available)) + \
                    " als je toch een andere soort oefening wilt doen."

        return [SlotSet("general_activity_activities_options_slot", sentence),
                SlotSet("rnd_activities_ids", available_activities_ids)]


class CheckUserInputRequired(Action):
    """Check if the activity requires the input of the user"""

    def name(self):
        return "check_user_input_required"

    async def run(self, dispatcher, tracker, domain):
        activity_id = tracker.get_slot('last_activity_id_slot')
        session = get_db_session()

        is_input_required = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )

        session.close()

        return [SlotSet("is_user_input_required", is_input_required[0].user_input_required)]


class CheckActivityDone(Action):
    """Check if an input for the activity has been
    already provided by the user"""

    def name(self):
        return "check_activity_done"

    async def run(self, dispatcher, tracker, domain):

        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)

        if user_inputs[-1].user_input is None:
            activity_done = False
        else:
            activity_done = True

        return [SlotSet("is_activity_done", activity_done)]


class ValidateActivityUsefulnessForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_activity_usefulness_form'

    def validate_activity_useful_rating(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate activity_useful_rating input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_activity_useful_rating':
            return {"activity_useful_rating": None}

        if not validator.validate_number_in_range_response(n_min=0, n_max=10,
                                                           response=value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"activity_useful_rating": None}

        return {"activity_useful_rating": value}


class ValidateSaveOrEditForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_save_or_edit_form'

    def validate_save_or_edit_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate save_or_edit_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_save_or_edit_slot':
            return {"save_or_edit_slot": None}

        if not self._validate_save_or_edit_response(value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"save_or_edit_slot": None}

        return {"save_or_edit_slot": value}

    @staticmethod
    def _validate_save_or_edit_response(value):
        if value in ('1', '2'):
            return True
        return False


class ValidateGeneralActivityDescriptionForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_general_activity_description_form'

    def validate_general_activity_description_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_description_slot input."""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_general_activity_description_slot':
            return {"general_activity_description_slot": None}

        if not validator.validate_long_enough_response_chars(value, 50):
            dispatcher.utter_message(response="utter_give_more_details")
            return {"general_activity_description_slot": None}

        return {"general_activity_description_slot": value}


class SaveDescriptionInDb(Action):
    def name(self) -> Text:
        return 'save_description_in_db'

    async def run(self, dispatcher, tracker, domain):
        """Save the provided description inf the DB."""

        description = tracker.get_slot('general_activity_description_slot')

        activity_id = tracker.get_slot('last_activity_id_slot')
        user_id = tracker.current_state()['sender_id']

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)
        row_id = user_inputs[-1].intervention_activities_performed_id

        session = get_db_session()

        session.execute(
            update(InterventionActivitiesPerformed)
            .where(InterventionActivitiesPerformed.intervention_activities_performed_id == row_id)
            .values(
                user_input=description
            )
        )

        session.commit()
        session.close()

        return []


class ValidateGeneralActivityNextActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_general_activity_next_activity_form'

    def validate_general_activity_activity_type_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_effort_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_general_activity_activity_type_slot':
            return {"general_activity_activity_type_slot": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"general_activity_activity_type_slot": None}

        user_id = tracker.current_state()['sender_id']

        activity_type_slot = int(value)
        activity_id = tracker.get_slot('last_activity_id_slot')

        activity_type = activities_categories[int(activity_type_slot)]

        _, available = get_possible_activities(user_id,
                                                       activity_type,
                                                       activity_id)

        available_activities_ids = [activity.intervention_activity_id for activity in available]

        options = ["Typ " + str(i + 1) + " als je '" +
                   available[i].intervention_activity_title +
                   "' wilt doen.\n"
                   for i in range(len(available))]

        sentence = str().join(options)

        sentence += "Typ " + \
                    str(len(available) + 1) + \
                    " als je toch een andere soort oefening wilt doen."

        dispatcher.utter_message(response="utter_general_activity_choose_next_activity_2")

        return {"general_activity_activity_type_slot": float(value),
                "general_activity_activities_options_slot": sentence,
                "rnd_activities_ids": available_activities_ids}

    def validate_general_activity_next_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate general_activity_next_activity_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_general_activity_next_activity_slot':
            return {"general_activity_next_activity_slot": None}

        opt_number = len(tracker.get_slot('rnd_activities_ids')) + 1

        if not validator.validate_number_in_range_response(1, opt_number, value):
            dispatcher.utter_message(text="Kun je een geheel getal tussen 1 en "
                                          + str(opt_number) + " opgeven? ...")
            return {"general_activity_next_activity_slot": None}

        if value == str(opt_number):
            return {"general_activity_activity_type_slot": None,
                    "general_activity_next_activity_slot": None}

        activity_type_slot = tracker.get_slot('general_activity_activity_type_slot')

        return {"general_activity_activity_type_slot": activity_type_slot,
                "general_activity_next_activity_slot": value}


class GetLastPerformedActivity(Action):
    """Get the last performed activity"""

    def name(self):
        return "get_last_performed_activity"

    async def run(self, dispatcher, tracker, domain):
        # get the last completed activity from DB and populate the slot

        session = get_db_session()
        user_id = tracker.current_state()['sender_id']
        last_activity = (
            session.query(
                InterventionActivitiesPerformed
            )
            .order_by(InterventionActivitiesPerformed.completed_datetime.desc())
            .filter(
                InterventionActivitiesPerformed.users_nicedayuid == user_id
            ).all()
        )

        if last_activity is not None:
            activity_title = last_activity[0].intervention_activity.intervention_activity_title
            activity_id = last_activity[0].intervention_activity.intervention_activity_id

            session.close()

            return [SlotSet("last_activity_slot", activity_title),
                    SlotSet("last_activity_id_slot", activity_id)]

        session.close()

        return [SlotSet("last_activity_slot", None),
                SlotSet("last_activity_id_slot", None)]


class GetActivityCoachChoice(Action):
    """The coach chooses the next activity and saves it in the slot"""

    def name(self):
        return "get_activity_coach_choice"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        mandatory, _ = get_possible_activities(user_id)
        activity_description = mandatory[0].intervention_activity_description
        mandatory_ids = [activity.intervention_activity_id for activity in mandatory]
        return [SlotSet("general_activity_chosen_activity_description_slot", activity_description),
                SlotSet("general_activity_next_activity_slot", 1),
                SlotSet("rnd_activities_ids",  mandatory_ids)]


class CheckWhoDecides(Action):
    """Check if the user or the coach decides the next activity"""

    def name(self):
        return "check_who_decides"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()['sender_id']
        mandatory, _ = get_possible_activities(user_id)

        if len(mandatory) > 0:
            decider = 'coach'
        else:
            decider = 'user'

        return [SlotSet("who_decides_slot", decider)]


class LoadActivity(Action):
    """load the activity instructions"""

    def name(self):
        return "load_activity"

    async def run(self, dispatcher, tracker, domain):

        chosen_option = int(tracker.get_slot('general_activity_next_activity_slot')) - 1
        activities_slot = tracker.get_slot('rnd_activities_ids')
        user_id = tracker.current_state()['sender_id']

        activity_id = activities_slot[chosen_option]
        session = get_db_session()

        user_inputs = get_user_intervention_activity_inputs(user_id, activity_id)

        if user_inputs:
            previous_input = user_inputs[-1].user_input
        else:
            previous_input = None

        # save the activity to the DB
        session.add(
            InterventionActivitiesPerformed(users_nicedayuid=user_id,
                                            intervention_activity_id=activity_id,
                                            user_input=previous_input)
        )

        session.commit()

        # get the instructions
        instructions = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )

        # prompt the message
        dispatcher.utter_message(text=instructions[0].intervention_activity_full_instructions)

        session.close()

        return []
    
    
class LoadActivityDescription(Action):
    """load the activity description"""

    def name(self):
        return "load_activity_description"

    async def run(self, dispatcher, tracker, domain):

        chosen_option = int(tracker.get_slot('general_activity_next_activity_slot')) - 1
        activities_slot = tracker.get_slot('rnd_activities_ids')

        activity_id = activities_slot[chosen_option]
        session = get_db_session()

        # get the description
        descriptions = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).one_or_none()
        )

        description = descriptions.intervention_activity_description

        session.close()

        # prompt the message
        return [SlotSet("general_activity_chosen_activity_description_slot",
                        description)]


class SetSlotGeneralActivity(Action):
    def name(self):
        return "action_set_slot_general_activity"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.GENERAL_ACTIVITY)]


def save_activity_to_fak(user_id: int, activity_id: int, rating_value: int):
    session = get_db_session()

    session.add(
        FirstAidKit(users_nicedayuid=user_id,
                    intervention_activity_id=activity_id,
                    activity_rating=rating_value)
    )
    session.commit()
    session.close()


class ValidatePersuasionReflectionForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_reflection_form'

    def validate_persuasion_reflection_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_reflection_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_reflection_slot':
            return {"persuasion_reflection_slot": None}

        if not validator.validate_long_enough_response_chars(value, 10):
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"persuasion_reflection_slot": None}

        return {"persuasion_reflection_slot": value}


class SavePersuasionToDatabase(Action):
    """Save persuasion to database"""

    def name(self):
        return "save_persuasion_to_database"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        # Get chosen persuasion type
        pers_type = tracker.get_slot('persuasion_type')
        # Get index of chosen persuasive message; -1 if "no persuasion"
        message_idx = tracker.get_slot("persuasive_message_index")
        # Get answers to state feature questions
        want = tracker.get_slot('persuasion_want_slot')
        prompts = tracker.get_slot('persuasion_prompts_slot')
        need = tracker.get_slot('persuasion_need_slot')
        # Get effort score
        effort = tracker.get_slot('persuasion_effort_slot')

        # Store state feature values to database
        store_dialog_closed_answer_to_db(user_id, answer_value=want,
                                         question_id=DialogQuestionsEnum.PERSUASION_WANT.value)
        store_dialog_closed_answer_to_db(user_id, answer_value=need,
                                         question_id=DialogQuestionsEnum.PERSUASION_NEED.value)
        store_dialog_closed_answer_to_db(user_id, answer_value=prompts,
                                         question_id=DialogQuestionsEnum.PERSUASION_PROMPTS.value)
        # Store used persuasion type (1 = commitment, 2 = consensus, 3 = no persuasion)
        store_dialog_closed_answer_to_db(user_id, answer_value=pers_type,
                                         question_id=DialogQuestionsEnum.PERSUASION_TYPE.value)
        # +2 since the lowest value we have is -1 in case of no persuasion, and the 
        # answer values must start at 1 in the database
        question_id = DialogQuestionsEnum.PERSUASION_MESSAGE_INDEX.value
        store_dialog_closed_answer_to_db(user_id, answer_value=message_idx + 2,
                                         question_id=question_id)
        # +1 since the lowest value is 0
        # Effort is None the first time the general activity dialog is run for a user
        if effort is not None:
            store_dialog_closed_answer_to_db(
                user_id, answer_value=effort + 1,
                question_id=DialogQuestionsEnum.PERSUASION_EFFORT.value)

        return []


def get_opt_persuasion_type(tracker: Tracker):
    """
    Get optimal persuasion type for user state.
    """

    # Get answers to state feature questions
    want = tracker.get_slot('persuasion_want_slot')
    prompts = tracker.get_slot('persuasion_prompts_slot')
    need = tracker.get_slot('persuasion_need_slot')

    # Make state binary
    binary_state = [want >= STATE_FEATURE_MEANS[0],
                    prompts >= STATE_FEATURE_MEANS[1],
                    need >= STATE_FEATURE_MEANS[2]]

    # Get optimal persuasion type
    pers_type = OPT_POLICY[binary_state[0]][binary_state[1]][binary_state[2]]

    return pers_type


class SendPersuasiveMessageActivity(Action):
    """Choose persuasion type and send persuasive message (if any)"""

    def name(self):
        return "send_persuasive_message_activity"

    async def run(self, dispatcher, tracker, domain):
        chosen_option = int(tracker.get_slot('general_activity_next_activity_slot'))
        activities_slot = tracker.get_slot('rnd_activities_ids')

        activity_id = activities_slot[chosen_option - 1]

        session = get_db_session()

        # Get the activity benefit
        activities = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).all()
        )
        benefit = activities[0].intervention_activity_benefit

        # Get optimal persuasion type for user state
        pers_type = get_opt_persuasion_type(tracker)

        reflective_question = ""  # Reflective question to ask users as part of persuasion
        input_required = False  # Whether we will ask a reflective question to users
        message_idx = -1  # Index of persuasive message
        # Commitment
        if pers_type == 1:
            input_required = True
            message_idx = random.randrange(len(COMMITMENT))
            dispatcher.utter_message(text=COMMITMENT[message_idx])
            # Not identity-based formulation
            if message_idx < 4:
                reflective_question = REFLECTIVE_QUESTION_COMMITMENT
            # Identity-based formulation
            else:
                reflective_question = REFLECTIVE_QUESTION_COMMITMENT_IDENTITY
        # Consensus
        elif pers_type == 2:
            input_required = True
            message_idx = random.randrange(len(CONSENSUS))
            dispatcher.utter_message(text=CONSENSUS[message_idx] + " " + benefit)
            reflective_question = REFLECTIVE_QUESTION_CONSENSUS

        session.close()
        return [SlotSet("persuasion_type", pers_type),
                SlotSet("persuasive_message_index", message_idx),
                SlotSet("persuasion_requires_input", input_required),
                SlotSet("persuasion_reflective_question", reflective_question)]


class ValidatePersuasionWantForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_want_form'

    def validate_persuasion_want_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_want_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_want_slot':
            return {"persuasion_want_slot": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_want_slot": None}

        return {"persuasion_want_slot": float(value)}


class ValidatePersuasionNeedForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_need_form'

    def validate_persuasion_need_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_need_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_need_slot':
            return {"persuasion_need_slot": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_need_slot": None}

        return {"persuasion_need_slot": float(value)}


class ValidatePersuasionPromptsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_prompts_form'

    def validate_persuasion_prompts_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_prompts_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_prompts_slot':
            return {"persuasion_prompts_slot": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"persuasion_prompts_slot": None}

        return {"persuasion_prompts_slot": float(value)}


class ValidatePersuasionEffortForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_persuasion_effort_form'

    def validate_persuasion_effort_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_effort_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_persuasion_effort_slot':
            return {"persuasion_effort_slot": None}

        if not validator.validate_number_in_range_response(0, 10, value):
            dispatcher.utter_message(response="utter_please_answer_0_to_10")
            return {"persuasion_effort_slot": None}

        return {"persuasion_effort_slot": float(value)}
