"""
Contains custom actions related to the relapse dialogs
"""

import logging

from . import validator
from .definitions import DATABASE_URL, REDIS_URL
from .helper import get_latest_bot_utterance, get_random_activities
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction, ActionExecuted, UserUttered, ReminderScheduled
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text, List
from virtual_coach_db.dbschema.models import InterventionActivity
from virtual_coach_db.helper.helper_functions import get_db_session

celery = Celery(broker=REDIS_URL)


class ActionResetOneFourSlot(Action):
    def name(self):
        return "action_reset_one_four_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('one_four_slot', None)]


class ActionResetOneOrTwoSlot(Action):
    def name(self):
        return "action_reset_one_or_two_slot"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('one_or_two_slot', None)]


class ActionSetSlotRelapseDialog(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_hrs"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('current_intervention_component', 'relapse_dialog_hrs')]


class ActionSetSlotRelapseDialogLapse(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_lapse"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('current_intervention_component', 'relapse_dialog_lapse')]


class ActionSetSlotRelapseDialogRelapse(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_relapse"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('current_intervention_component', 'relapse_dialog_relapse')]


class PopulateCopingActivitiesList(Action):
    def name(self):
        return "populate_coping_activities_list"

    async def run(self, dispatcher, tracker, domain):
        # TODO: instead of querying the whole list of activities, use only the selected ones
        # list of activities to be provided by content team
        rnd_activities = get_random_activities(-1, 3)
        rnd_activities_ids = [activity.intervention_activity_id for activity in rnd_activities]

        return [SlotSet('coping_activities_ids', rnd_activities_ids),
                SlotSet('coping_activity1_name', rnd_activities[0].intervention_activity_title),
                SlotSet('coping_activity2_name', rnd_activities[1].intervention_activity_title),
                SlotSet('coping_activity3_name', rnd_activities[2].intervention_activity_title)]


# Trigger relapse phase through celery
class TriggerRelapseDialog(Action):
    def name(self):
        return "action_trigger_relapse"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        slot = tracker.get_slot("current_intervention_component")
        logging.info(slot)

        celery.send_task('celery_tasks.relapse_dialog', (user_id, slot))
        logging.info("no celery error")

        return []


class ShowChosenCopingActivity(Action):
    def name(self):
        return "show_chosen_coping_activity"

    async def run(self, dispatcher, tracker, domain):
        chosen_option = int(tracker.get_slot('hrs_choose_coping_activity_slot'))
        activities_slot = tracker.get_slot('coping_activities_ids')

        activity_id = activities_slot[chosen_option - 1]

        session = get_db_session(db_url=DATABASE_URL)

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

        return []


class ShowBarchartDifficultSituations(Action):
    def name(self):
        return "show_barchart_difficult_situations"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        # TODO: plot barchart, save and send

        return []


class ShowFirstCopingActivity(Action):
    def name(self):
        return "show_first_coping_activity"

    async def run(self, dispatcher, tracker, domain):
        activity_id = tracker.get_slot('hrs_coping_activities_performed')

        activities_list = get_random_activities(int(activity_id), 1)

        dispatcher.utter_message(activities_list[0].intervention_activity_full_instructions)

        return [SlotSet('hrs_coping_activities_performed', activity_id)]


class StoreHrsSituation(Action):
    def name(self):
        return "store_hrs_situation"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_situation_slot')

        # TODO: save on DB

        return []


class StoreHrsFeeling(Action):
    def name(self):
        return "store_hrs_feeling"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_feeling_slot')

        # TODO: save on DB

        return []


class StoreHrsWhoWith(Action):
    def name(self):
        return "store_hrs_who_with"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_who_with_slot')

        # TODO: save on DB

        return []


class StoreHrsWhatHappened(Action):
    def name(self):
        return "store_hrs_what_happened"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_what_happened_slot')

        # TODO: save on DB

        return []


class ValidateSmokeOrPaForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_smoke_or_pa_form'

    def validate_smoke_or_pa(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate smoke or pa input."""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_smoke_or_pa_form_smoke_or_pa':
            return {"smoke_or_pa": None}

        logging.info("Performing the action to validate smoke_or_pa_form")  # Debug message
        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"smoke_or_pa": None}

        return {"smoke_or_pa": value}


class ValidateCraveLapseRelapseForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_crave_lapse_relapse_form'

    def validate_crave_lapse_relapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate crave, lapse or relapse input."""
        logging.info("Performing the action to validate crave lapse relapse form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_crave_lapse_relapse':
            return {"crave_lapse_relapse": None}

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"crave_lapse_relapse": None}

        return {"crave_lapse_relapse": value}


class ValidateEhboMeSelfForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_ehbo_me_self_form'

    def validate_ehbo_me_self(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate ehbo, me or self input"""

        logging.info("Validate ehbo me self form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_ehbo_me_self':
            return {"ehbo_me_self": None}

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
            return {"ehbo_me_self": None}

        return {"ehbo_me_self": value}


class ValidateTypeAndNumberSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_type_and_number_smoke_form'

    def validate_type_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input"""

        logging.info("Validate type smoke form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke':
            return {"type_smoke": None}

        if not validator.validate_number_in_range_response(1, 4, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"type_smoke": None}

        return {"type_smoke": value}

    def validate_type_smoke_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input confirmation"""

        logging.info("Validate type smoke form confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke_confirm':
            return {"type_smoke_confirm": None}

        if not validator.validate_yes_no_answer(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"type_smoke_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"type_smoke": None, "type_smoke_confirm": None}
        else:
            return {"type_smoke_confirm": value}

    def validate_number_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smokes"""

        logging.info("Validate type number smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke':
            return {"number_smoke": None}

        if not validator.validate_int_type(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"number_smoke": None}

        return {"number_smoke": value}

    def validate_number_smoke_confirm(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smoke input confirmation"""

        logging.info("Validate number smoke form confirmation")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke_confirm':
            return {"number_smoke_confirm": None}

        if not validator.validate_yes_no_answer(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_yes_no")
            return {"number_smoke_confirm": None}

        if value.lower() in ['Nee', 'nee', "nee."]:
            return {"number_smoke": None, "number_smoke_confirm": None}
        else:
            return {"number_smoke_confirm": value}


class ValidateWhatDoingHowFeelSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_what_doing_how_feel_smoke_form'

    def validate_what_doing_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate what doing while smoking"""
        max_val = 7
        logging.info("Validate what doing smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_what_doing_smoke':
            return {"what_doing_smoke": None}

        is_valid = validator.validate_list(value, 1, max_val)

        if is_valid is False:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"what_doing_smoke": None}

        return {"what_doing_smoke": value}

    def validate_how_feel_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate type of smoke input confirmation"""
        logging.info("Validate how feel smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_feel_smoke':
            return {"how_feel_smoke": None}

        valid = validator.validate_list(value, 0, 5)

        if not valid:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"how_feel_smoke": None}

        return {"how_feel_smoke": value}


class ValidateWithWhomEventSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_with_whom_event_smoke_form'

    def validate_with_whom_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate with whom smoke """
        max_val = 6
        logging.info("Validate with whom smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_with_whom_smoke':
            return {"with_whom_smoke": None}

        valid = validator.validate_list(value, 0, 6)

        if not valid:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"with_whom_smoke": None}

        return {"with_whom_smoke": value}

    def validate_event_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate event smoke"""
        logging.info("Validate event smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_event_smoke':
            return {"with_whom_smoke": None}

        return {"with_whom_smoke": value}


class ValidateReflectBarChartForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_reflect_bar_chart_form'

    def validate_reflect_bar_chart(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate reflect bar chart"""
        logging.info("Validate with whom smoke")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_reflect_bar_chart':
            return {"reflect_bar_chart": None}

        long_enough_response = validator.validate_long_enough_response_words(value, 5)
        if not long_enough_response:
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"reflect_bar_chart": None}

        return {"reflect_bar_chart": value}


class ValidatePaTypeTogetherWhyFailForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_type_together_why_fail_form'

    def validate_pa_type(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_type"""
        logging.info("Validate type smoke relapse form")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_type':
            return {"pa_type": None}

        return {"pa_type": value}

    def validate_pa_together(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_ together"""
        logging.info("Validate type pa together")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_together':
            return {"pa_together": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"pa_together": None}

        return {"pa_together": value}

    def validate_pa_why_fail(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa why fail"""
        max_val = 7
        logging.info("Validate pa why fail")  # Debug message

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_why_fail':
            return {"pa_why_fail": None}

        value = self._input_to_list(value, max_val)

        if not validator.validate_list(value, 0, max_val):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_numbers")
            return {"pa_why_fail": None}

        return {"pa_why_fail": value}


class ValidateHrsNewActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_new_activity_form'

    def validate_hrs_new_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_new_activity_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_new_activity_slot':
            return {"hrs_new_activity_slot": None}

        is_valid = validator.validate_number_in_range_response(1, 2, value)
        if not is_valid:
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"hrs_new_activity_slot": None}

        return {"hrs_new_activity_slot": value}


class ValidateHrsSituationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_situation_form'

    def validate_hrs_situation_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_situation_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_situation_slot':
            return {"hrs_situation_slot": None}

        is_valid = validator.validate_list(value, 1, 7)
        if not is_valid:
            dispatcher.utter_message(response="utter_please_answer_1_to_7")
            return {"hrs_situation_slot": None}

        return {"hrs_situation_slot": value}


class ValidateHrsFeelingForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_feeling_form'

    def validate_hrs_feeling_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_feeling_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_feeling_slot':
            return {"hrs_feeling_slot": None}

        is_valid = validator.validate_list(value, 1, 8)
        if not is_valid:
            dispatcher.utter_message(response="utter_please_answer_1_to_8")
            return {"hrs_feeling_slot": None}

        return {"hrs_feeling_slot": value}


class ValidateHrsWhoWithForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_who_with_form'

    def validate_hrs_who_with_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_who_with_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_who_with_slot':
            return {"hrs_who_with_slot": None}

        is_valid = validator.validate_list(value, 1, 6)
        if not is_valid:
            dispatcher.utter_message(response="utter_please_answer_1_to_6")
            return {"hrs_who_with_slot": None}

        return {"hrs_who_with_slot": value}


class ValidateHrsWhatHappenedForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_what_happened_form'

    def validate_hrs_what_happened_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_what_happened_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_what_happened_slot':
            return {"hrs_what_happened_slot": None}

        return {"hrs_what_happened_slot": value}


class ValidateHrsLikeFeedbackForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_like_feedback_form'

    def validate_hrs_like_feedback_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_like_feedback_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_like_feedback_slot':
            return {"hrs_like_feedback_slot": None}
        if not validator.validate_long_enough_response_chars(value, 50):
            dispatcher.utter_message(response="utter_please_answer_more_words")
            return {"hrs_like_feedback_slot": None}

        return {"hrs_like_feedback_slot": value}


class ValidateHrsEnoughMotivationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_enough_motivation_form'

    def validate_hrs_enough_motivation_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_enough_motivation_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_enough_motivation_slot':
            return {"hrs_enough_motivation_slot": None}
        print("VALID MOTIVATION SLOT")
        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"hrs_enough_motivation_slot": None}

        return {"hrs_enough_motivation_slot": value}


class ValidateHrsActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_activity_form'

    def validate_hrs_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate validate_hrs_activity_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_activity_slot':
            return {"hrs_activity_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"hrs_activity_slot": None}
        return {"hrs_activity_slot": value}


class ValidateHrsChooseCopingActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_choose_coping_activity_form'

    def validate_hrs_choose_coping_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate hrs_choose_coping_activity_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_hrs_choose_coping_activity_slot':
            return {"hrs_choose_coping_activity_slot": None}

        if not validator.validate_number_in_range_response(1, 4, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"hrs_choose_coping_activity_slot": None}

        if value == '4':
            rnd_activities = get_random_activities(-1, 3)
            rnd_activities_ids = [activity.intervention_activity_id for activity in rnd_activities]

            return {"hrs_choose_coping_activity_slot": None,
                    "coping_activities_ids": rnd_activities_ids,
                    "coping_activity1_name": rnd_activities[0].intervention_activity_title,
                    "coping_activity2_name": rnd_activities[1].intervention_activity_title,
                    "coping_activity3_name": rnd_activities[2].intervention_activity_title}

        return {"hrs_choose_coping_activity_slot": value}


class ValidateEhboMeSelfLapseForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_ehbo_me_self_lapse_form'

    def validate_ehbo_me_self_lapse(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate ehbo, me or self input"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_ehbo_me_self_lapse':
            return {"ehbo_me_self_lapse": None}

        if not validator.validate_number_in_range_response(1, 4, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"ehbo_me_self_lapse": None}

        return {"ehbo_me_self_lapse": value}


class ValidateRelapseStopNowLaterForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_relapse_stop_now_later_form'

    def validate_one_or_two_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate one_or_two_slot"""
        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_relapse_stop_now_later_form_one_or_two_slot':
            return {"one_or_two_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"one_or_two_slot": None}

        return {"one_or_two_slot": value}


class ValidateRelapseMedicationInfoForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_relapse_medication_info_form'

    def validate_one_or_two_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate one_or_two_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_relapse_medication_info_form_one_or_two_slot':
            return {"one_or_two_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"one_or_two_slot": None}

        return {"one_or_two_slot": value}


class ValidateLapseEhboForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_lapse_ehbo_form'

    def validate_lapse_ehbo_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate lapse_ehbo_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_lapse_ehbo_form_lapse_ehbo_slot':
            return {"lapse_ehbo_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"lapse_ehbo_slot": None}

        return {"lapse_ehbo_slot": value}