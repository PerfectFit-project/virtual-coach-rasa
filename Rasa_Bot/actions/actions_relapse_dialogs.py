"""
Contains custom actions related to the relapse dialogs
"""

import logging
import secrets

from . import validator
from .definitions import REDIS_URL, activities_categories
from .helper import (figure_has_data,
                     get_latest_bot_utterance, 
                     get_possible_activities,
                     populate_fig,
                     store_dialog_closed_answer_list_to_db,
                     store_dialog_closed_answer_to_db,
                     store_dialog_open_answer_to_db,
                     mark_completion)
from celery import Celery
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from typing import Any, Dict, Text
from virtual_coach_db.helper.definitions import (Components,
                                                 DialogQuestionsEnum)
from virtual_coach_db.helper.helper_functions import get_db_session
from virtual_coach_db.dbschema.models import InterventionActivity
from plotly.subplots import make_subplots

celery = Celery(broker=REDIS_URL)


class ActionCheckReasons(Action):
    def name(self):
        return "action_check_reasons"

    async def run(self, dispatcher, tracker, domain):
        reasons = tracker.get_slot('pa_why_fail')

        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        slot = tracker.get_slot("current_intervention_component")

        if '6' in reasons:
            dispatcher.utter_message(response="utter_pa_sick")
            mark_completion(user_id, slot)
            return [FollowupAction('action_end_dialog')]

        return []


class ActionLaunchGoalSetting(Action):
    def name(self):
        return "action_launch_goal_setting"

    async def run(self, dispatcher, tracker, domain):
        # starts the rule for setting a new quit date in the goal setting dialog
        return [FollowupAction('action_get_first_last_date')]


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


class ActionSetSlotSmokeOrPa1(Action):
    def name(self):
        return "action_set_slot_smoke_or_pa_1"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('smoke_or_pa', 1)]


class ActionSetSlotSmokeOrPa2(Action):
    def name(self):
        return "action_set_slot_smoke_or_pa_2"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('smoke_or_pa', 2)]


class ActionSetSlotsCraveLapseRelapse1(Action):
    def name(self):
        return "action_set_slot_crave_lapse_relapse_1"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('crave_lapse_relapse', 1)]


class ActionSetSlotCraveLapseRelapse2(Action):
    def name(self):
        return "action_set_slot_crave_lapse_relapse_2"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('crave_lapse_relapse', 2)]


class ActionSetSlotCraveLapseRelapse3(Action):
    def name(self):
        return "action_set_slot_crave_lapse_relapse_3"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('crave_lapse_relapse', 3)]


class ActionResetSlotCraveLapseRelapse(Action):
    def name(self):
        return "action_reset_slot_crave_lapse_relapse"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet('crave_lapse_relapse', None)]


class ActionSetSlotWeeklyOrRelapse(Action):
    def name(self):
        return "action_set_slot_weekly_or_relapse"

    async def run(self, dispatcher, tracker, domain):
        intervention_component = tracker.get_slot('current_intervention_component')

        if intervention_component == Components.WEEKLY_REFLECTION:
            return [SlotSet('weekly_or_relapse', 2)]

        return [SlotSet('weekly_or_relapse', 1)]


class ActionSetSlotRelapseDialog(Action):
    def name(self):
        return "action_set_slot_relapse_dialog"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("current_intervention_component",
                        Components.RELAPSE_DIALOG)]


class ActionSetSlotRelapseDialogHrs(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_hrs"

    async def run(self, dispatcher, tracker, domain):

        return [SlotSet('current_intervention_component',
                        Components.RELAPSE_DIALOG_HRS)]


class ActionSetSlotRelapseDialogLapse(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_lapse"

    async def run(self, dispatcher, tracker, domain):

        return [SlotSet('current_intervention_component',
                        Components.RELAPSE_DIALOG_LAPSE)]


class ActionSetSlotRelapseDialogPa(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_pa"

    async def run(self, dispatcher, tracker, domain):

        logging.info('set PA slot')
        return [SlotSet('current_intervention_component',
                        Components.RELAPSE_DIALOG_PA)]


class ActionSetSlotRelapseDialogRelapse(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_relapse"

    async def run(self, dispatcher, tracker, domain):

        return [SlotSet('current_intervention_component',
                        Components.RELAPSE_DIALOG_RELAPSE)]


class ActionSetSlotRelapseDialogSystem(Action):
    def name(self):
        return "action_set_slot_relapse_dialog_system"

    async def run(self, dispatcher, tracker, domain):
        # set the current intervention component and the slots needed
        # to proceed correctly in the dialog
        return [SlotSet('current_intervention_component', Components.RELAPSE_DIALOG_SYSTEM),
                SlotSet('smoke_or_pa', 2),
                SlotSet('weekly_or_relapse', 1)]


# Trigger relapse phase through celery
class TriggerRelapseDialog(Action):
    def name(self):
        return "action_trigger_relapse"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        celery.send_task('celery_tasks.user_trigger_dialog',
                         (user_id, Components.RELAPSE_DIALOG))

        return []


class ValidateHrsChooseCopingActivityForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_hrs_choose_coping_activity_form'

    def validate_hrs_choose_coping_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate persuasion_effort_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_hrs_choose_coping_activity_slot':
            return {"hrs_choose_coping_activity_slot": None}

        if not validator.validate_number_in_range_response(1, 5, value):
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4_5")
            return {"hrs_choose_coping_activity_slot": None}

        user_id = tracker.current_state()['sender_id']

        activity_type_slot = int(value)

        activity_type = activities_categories[int(activity_type_slot)]

        smoke_or_pa = int(tracker.get_slot('smoke_or_pa'))

        # in the PA branch an activity (22) has to be avoided
        avoid_id = None
        if smoke_or_pa == 2:
            avoid_id = 22

        _, available = get_possible_activities(user_id,
                                               activity_type,
                                               avoid_id)

        available_activities_ids = [activity.intervention_activity_id for activity in available]

        options = ["Typ " + str(i + 1) + " als je " +
                   available[i].intervention_activity_title +
                   " wilt doen.\n"
                   for i in range(len(available))]

        sentence = ''.join(options)

        sentence += "Typ " + \
                    str(len(available) + 1) + \
                    " als je toch een andere soort oefening wilt doen."

        dispatcher.utter_message(response="utter_ask_hrs_choose_coping_activity2")

        return {"hrs_choose_coping_activity_slot": float(value),
                "hrs_coping_activity_activities_options_slot": sentence,
                "rnd_activities_ids": available_activities_ids}

    def validate_coping_activity_next_activity_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate coping_activity_next_activity_slot input."""
        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_coping_activity_next_activity_slot':
            return {"coping_activity_next_activity_slot": None}

        opt_number = len(tracker.get_slot('rnd_activities_ids')) + 1

        if not validator.validate_number_in_range_response(1, opt_number, value):
            dispatcher.utter_message(text="Kun je een geheel getal tussen 1 en "
                                          + str(opt_number) + " opgeven? ...")
            return {"coping_activity_next_activity_slot": None}

        if value == str(opt_number):
            return {"hrs_choose_coping_activity_slot": None,
                    "coping_activity_next_activity_slot": None}

        activity_type_slot = tracker.get_slot('hrs_choose_coping_activity_slot')

        return {"hrs_choose_coping_activity_slot": activity_type_slot,
                "coping_activity_next_activity_slot": value}


class ShowChosenCopingActivity(Action):
    def name(self):
        return "show_chosen_coping_activity"

    async def run(self, dispatcher, tracker, domain):
        chosen_option = int(tracker.get_slot('coping_activity_next_activity_slot'))
        activities_slot = tracker.get_slot('rnd_activities_ids')

        activity_id = activities_slot[chosen_option - 1]

        session = get_db_session()

        instructions = (
            session.query(
                InterventionActivity
            )
            .filter(
                InterventionActivity.intervention_activity_id == activity_id
            ).first()
        )

        # prompt the message
        dispatcher.utter_message(text=instructions.intervention_activity_full_instructions)

        session.close()

        return []


class ShowBarchartDifficultSituations(Action):
    def name(self):
        return "show_barchart_difficult_situations"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=("Wat was je aan het doen?",
                            "Hoe voelde je je?",
                            "Met wie was je?")
        )

        legends = [("Trek kreeg", "yellow"), ("Rookte", "red")]

        question_ids = [[[DialogQuestionsEnum.RELAPSE_CRAVING_WHAT_DOING.value],
                        [DialogQuestionsEnum.RELAPSE_LAPSE_WHAT_DOING.value,
                        DialogQuestionsEnum.RELAPSE_RELAPSE_WHAT_DOING.value]],
                        [[DialogQuestionsEnum.RELAPSE_CRAVING_HOW_FEEL.value],
                         [DialogQuestionsEnum.RELAPSE_LAPSE_HOW_FEEL.value,
                         DialogQuestionsEnum.RELAPSE_RELAPSE_HOW_FEEL.value]],
                        [[DialogQuestionsEnum.RELAPSE_CRAVING_WITH_WHOM.value],
                         [DialogQuestionsEnum.RELAPSE_LAPSE_WITH_WHOM.value,
                         DialogQuestionsEnum.RELAPSE_RELAPSE_WITH_WHOM.value]]]

        fig = populate_fig(fig, question_ids, user_id, legends)

        fig.update_layout(height=1200, width=800, title_text="Op deze grafieken zie je hoe vaak je"
                                     " in een bepaalde situatie was toen je")

        filepath = '/app/barchart_difficult_situations.PNG'

        try:
            fig.write_image("barchart_difficult_situations.PNG")
        except Exception:
            logging.info("File upload unsuccessful.")

        return [SlotSet("upload_file_path", filepath)]
    

class ActionCheckBarchartDifficultSituationsHasData(Action):
    def name(self):
        return "action_check_barchart_difficult_situations_has_data"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        
        question_ids = [[[DialogQuestionsEnum.RELAPSE_CRAVING_WHAT_DOING.value],
                        [DialogQuestionsEnum.RELAPSE_LAPSE_WHAT_DOING.value,
                        DialogQuestionsEnum.RELAPSE_RELAPSE_WHAT_DOING.value]],
                        [[DialogQuestionsEnum.RELAPSE_CRAVING_HOW_FEEL.value],
                         [DialogQuestionsEnum.RELAPSE_LAPSE_HOW_FEEL.value,
                         DialogQuestionsEnum.RELAPSE_RELAPSE_HOW_FEEL.value]],
                        [[DialogQuestionsEnum.RELAPSE_CRAVING_WITH_WHOM.value],
                         [DialogQuestionsEnum.RELAPSE_LAPSE_WITH_WHOM.value,
                         DialogQuestionsEnum.RELAPSE_RELAPSE_WITH_WHOM.value]]]

        # check if there is already data for the figure
        has_data = figure_has_data(question_ids, user_id)

        return [SlotSet("figure_previous_difficult_smoking_situations_has_data", has_data)]


class ShowBarchartDifficultSituationsPa(Action):
    def name(self):
        return "show_barchart_difficult_situations_pa"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=("Wat je overdag verder deed?",
                            "Reden niet lichamelijk actief",
                            "Zou je met iemand actief zijn?")
        )

        legends = [("Obstakels bewegen", "blue")]

        question_ids = [[[DialogQuestionsEnum.RELAPSE_PA_DOING_TODAY.value]],
                        [[DialogQuestionsEnum.RELAPSE_PA_WHY_FAIL.value]],
                        [[DialogQuestionsEnum.RELAPSE_PA_TOGETHER.value]]]
        
        # check if there is already data for the figure
        has_data = figure_has_data(question_ids, user_id)

        fig = populate_fig(fig, question_ids, user_id, legends)

        fig.update_layout(height=1200, width=800, title_text="Op deze grafieken"
                          " zie je hoe vaak je in een bepaalde situatie was toen <br>"
                          "het moeilijk vond om in beweging te komen",
                          showlegend=False)

        filepath = '/app/barchart_difficult_situations_pa.PNG'

        try:
            fig.write_image("barchart_difficult_situations_pa.PNG")
        except Exception:
            logging.info("File upload unsuccessful.")

        return [SlotSet("upload_file_path", filepath),
                SlotSet("figure_previous_difficult_pa_situations_has_data", has_data)]


class ShowFirstCopingActivity(Action):
    def name(self):
        return "show_first_coping_activity"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])

        _, activities_list = get_possible_activities(user_id=user_id)
        random_choice = secrets.choice(activities_list)

        dispatcher.utter_message(random_choice.intervention_activity_full_instructions)


class ShowFirstCopingActivityPa(Action):
    def name(self):
        return "show_first_coping_activity_pa"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])
        # this activity has to be excluded for the PA branch
        avoid_activity = 22

        _, activities_list = get_possible_activities(user_id=user_id,
                                                     avoid_activity_id=avoid_activity)
        random_choice = secrets.choice(activities_list)

        dispatcher.utter_message(random_choice.intervention_activity_full_instructions)


class StoreCraveLapseRelapse(Action):
    def name(self):
        return "store_crave_lapse_relapse"

    async def run(self, dispatcher, tracker, domain):
        """
        store in the db which branch of the relapse dialog the user has selected
        (1 = crave, 2 = lapse, 3 = relapse)
        """
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = int(tracker.get_slot('crave_lapse_relapse'))

        question_id = DialogQuestionsEnum.RELAPSE_SMOKE_HRS_LAPSE_RELAPSE.value

        store_dialog_closed_answer_to_db(user_id,
                                         question_id,
                                         choice)
        return []


class StoreEventSmoke(Action):
    def name(self):
        return "store_event_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('event_smoke')
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_HAPPENED_SPECIAL.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_HAPPENED_SPECIAL.value

        store_dialog_open_answer_to_db(user_id,
                                       question_id,
                                       choice)

        return []


class StoreHowFeelSmoke(Action):
    def name(self):
        return "store_how_feel_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('how_feel_smoke')
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_HOW_FEEL.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_HOW_FEEL.value

        store_dialog_closed_answer_list_to_db(user_id,
                                              question_id,
                                              choice)

        return []


class StoreHrsSituation(Action):
    def name(self):
        return "store_hrs_situation"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_situation_slot')
        store_dialog_closed_answer_list_to_db(user_id,
                                              DialogQuestionsEnum.RELAPSE_CRAVING_WHAT_DOING.value,
                                              choice)

        return []


class StoreHrsFeeling(Action):
    def name(self):
        return "store_hrs_feeling"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_feeling_slot')

        store_dialog_closed_answer_list_to_db(user_id,
                                              DialogQuestionsEnum.RELAPSE_CRAVING_HOW_FEEL.value,
                                              choice)

        return []


class StoreHrsWhoWith(Action):
    def name(self):
        return "store_hrs_who_with"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_who_with_slot')

        store_dialog_closed_answer_list_to_db(user_id,
                                              DialogQuestionsEnum.RELAPSE_CRAVING_WITH_WHOM.value,
                                              choice)

        return []


class StoreHrsWhatHappened(Action):
    def name(self):
        return "store_hrs_what_happened"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('hrs_what_happened_slot')

        store_dialog_open_answer_to_db(user_id,
                                       DialogQuestionsEnum.RELAPSE_CRAVING_HAPPENED_SPECIAL.value,
                                       choice)

        return []


class StorePaSpecifyPa(Action):
    def name(self):
        return "store_pa_specify_pa"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = int(tracker.get_slot('pa_specify_pa_slot'))

        store_dialog_closed_answer_to_db(user_id,
                                         DialogQuestionsEnum.RELAPSE_PA_SPECIFY_PA.value,
                                         choice)
        return []


class StorePaType(Action):
    def name(self):
        return "store_pa_type"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('pa_type')

        store_dialog_open_answer_to_db(user_id,
                                       DialogQuestionsEnum.RELAPSE_PA_TYPE.value,
                                       choice)
        return []


class StorePaTogether(Action):
    def name(self):
        return "store_pa_together"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = int(tracker.get_slot('pa_together'))

        store_dialog_closed_answer_to_db(user_id,
                                         DialogQuestionsEnum.RELAPSE_PA_TOGETHER.value,
                                         choice)
        return []


class StorePaWhyFail(Action):
    def name(self):
        return "store_pa_why_fail"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('pa_why_fail')  # this is a list already validated

        store_dialog_closed_answer_list_to_db(user_id,
                                              DialogQuestionsEnum.RELAPSE_PA_WHY_FAIL.value,
                                              choice)
        return []


class StorePaDoingToday(Action):
    def name(self):
        return "store_pa_doing_today"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('pa_doing_today_slot')  # this is a list already validated

        store_dialog_closed_answer_list_to_db(user_id,
                                              DialogQuestionsEnum.RELAPSE_PA_DOING_TODAY.value,
                                              choice)
        return []


class StorePaHappenedSpecial(Action):
    def name(self):
        return "store_pa_happened_special"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('pa_happened_special_slot')

        store_dialog_open_answer_to_db(user_id,
                                       DialogQuestionsEnum.RELAPSE_PA_HAPPENED_SPECIAL.value,
                                       choice)
        return []


class StoreReflectBarchart(Action):
    def name(self):
        return "store_reflect_barchart"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('reflect_bar_chart')
        # check in which branch we are
        smoke_or_pa = int(tracker.get_slot('smoke_or_pa'))

        if smoke_or_pa == 1:
            crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))
            if crave_lapse_relapse == 1:
                question_id = DialogQuestionsEnum.RELAPSE_CRAVING_REFLECT_BARCHART.value
            elif crave_lapse_relapse == 2:
                question_id = DialogQuestionsEnum.RELAPSE_LAPSE_REFLECT_BARCHART.value
            elif crave_lapse_relapse == 3:
                question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_REFLECT_BARCHART.value
        elif smoke_or_pa == 2:
            question_id = DialogQuestionsEnum.RELAPSE_PA_REFLECT_BARCHART.value

        store_dialog_open_answer_to_db(user_id,
                                       question_id,
                                       choice)
        return []


class StoreTypeSmoke(Action):
    def name(self):
        return "store_type_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = int(tracker.get_slot('type_smoke'))
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_TYPE_SMOKE.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_TYPE_SMOKE.value

        store_dialog_closed_answer_to_db(user_id,
                                         question_id,
                                         choice)
        return []


class StoreNumberSmoke(Action):
    def name(self):
        return "store_number_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('number_smoke')
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_NUMBER_CIGARETTES.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_NUMBER_CIGARETTES.value

        store_dialog_open_answer_to_db(user_id,
                                       question_id,
                                       choice)
        return []


class StoreWhatDoingSmoke(Action):
    def name(self):
        return "store_what_doing_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('what_doing_smoke')
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_WHAT_DOING.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_WHAT_DOING.value
        store_dialog_closed_answer_list_to_db(user_id,
                                              question_id,
                                              choice)

        return []


class StoreWithWhomSmoke(Action):
    def name(self):
        return "store_with_whom_smoke"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID
        # get the user choice
        choice = tracker.get_slot('with_whom_smoke')
        crave_lapse_relapse = int(tracker.get_slot('crave_lapse_relapse'))

        if crave_lapse_relapse == 2:  # lapse
            question_id = DialogQuestionsEnum.RELAPSE_LAPSE_WITH_WHOM.value
        elif crave_lapse_relapse == 3:  # relapse
            question_id = DialogQuestionsEnum.RELAPSE_RELAPSE_WITH_WHOM.value

        store_dialog_closed_answer_list_to_db(user_id,
                                              question_id,
                                              choice)

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

        if not validator.validate_number_in_range_response(1, 3, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3")
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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_ehbo_me_self':
            return {"ehbo_me_self": None}
        
        first_aid_kit_filled = tracker.get_slot('first_aid_kit_filled')
        
        if first_aid_kit_filled:

            if not validator.validate_number_in_range_response(1, 3, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_1_2_3")
                return {"ehbo_me_self": None}
            
        else:
            # option 1 not available when first aid kit is empty
            if not validator.validate_number_in_range_response(2, 3, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_2_3")
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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_type_smoke':
            return {"type_smoke": None}

        if not validator.validate_number_in_range_response(1, 4, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"type_smoke": None}

        return {"type_smoke": value}

    def validate_number_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate number of smokes"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_number_smoke':
            return {"number_smoke": None}

        if not validator.validate_int_type(value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_number")
            return {"number_smoke": None}

        return {"number_smoke": value}


class ValidateWhatDoingHowFeelSmokeForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_what_doing_how_feel_smoke_form'

    def validate_what_doing_smoke(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate what doing while smoking"""
        max_val = 7

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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_how_feel_smoke':
            return {"how_feel_smoke": None}

        valid = validator.validate_list(value, 1, 9)

        if not valid:
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_to_9_multiple_numbers")
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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_with_whom_smoke':
            return {"with_whom_smoke": None}

        valid = validator.validate_list(value, 0, max_val)

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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_event_smoke':
            return {"event_smoke": None}

        return {"event_smoke": value}


class ValidateReflectBarChartForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_reflect_bar_chart_form'

    def validate_reflect_bar_chart(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate reflect bar chart"""

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
        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_type':
            return {"pa_type": None}

        return {"pa_type": value}

    def validate_pa_together(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_ together"""

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

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_why_fail':
            return {"pa_why_fail": None}

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

        is_valid = validator.validate_list(value, 1, 9)
        if not is_valid:
            dispatcher.utter_message(response="utter_please_answer_1_to_9_multiple_numbers")
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
        
        first_aid_kit_filled = tracker.get_slot('first_aid_kit_filled')
        
        if first_aid_kit_filled:

            if not validator.validate_number_in_range_response(1, 4, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
                return {"ehbo_me_self_lapse": None}
            
        else:
            # option 1 is removed when the first aid kit is empty
            if not validator.validate_number_in_range_response(2, 4, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_2_3_4")
                return {"ehbo_me_self_lapse": None}
            

        return {"ehbo_me_self_lapse": value}
    

class ValidateEhboMeSelfLapsePAForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_ehbo_me_self_lapse_pa_form'

    def validate_ehbo_me_self_lapse_pa(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate ehbo, me or self input"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_ehbo_me_self_lapse_pa':
            return {"ehbo_me_self_lapse_pa": None}
        
        first_aid_kit_filled = tracker.get_slot('first_aid_kit_filled')
        
        if first_aid_kit_filled:

            if not validator.validate_number_in_range_response(1, 4, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
                return {"ehbo_me_self_lapse_pa": None}
            
        else:
            # option 1 is removed when the first aid kit is empty
            if not validator.validate_number_in_range_response(2, 4, value):
                dispatcher.utter_message(response="utter_did_not_understand")
                dispatcher.utter_message(response="utter_please_answer_2_3_4")
                return {"ehbo_me_self_lapse_pa": None}
            

        return {"ehbo_me_self_lapse_pa": value}


class ValidateRelapseStopNowLaterForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_relapse_stop_now_later_form'

    def validate_now_or_later_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate now_or_later_slot"""
        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_now_or_later_slot':
            return {"now_or_later_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"now_or_later_slot": None}

        return {"now_or_later_slot": value}


class ValidateRelapseMedicationInfoForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_relapse_medication_info_form'

    def validate_medication_info_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate medication_info_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_medication_info_slot':
            return {"medication_info_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"medication_info_slot": None}

        return {"medication_info_slot": value}


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


class ValidatePaSpecifyPaForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_specify_pa_form'

    def validate_pa_specify_pa_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_specify_pa_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_pa_specify_pa_slot':
            return {"pa_specify_pa_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_2_3_4")
            return {"pa_specify_pa_slot": None}

        return {"pa_specify_pa_slot": value}


class ValidatePaContextEventsForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_doing_today_happened_special_form'

    def validate_pa_doing_today_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_doing_today_slot"""
        max_value = 7

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_pa_doing_today_slot':
            return {"pa_doing_today_slot": None}

        if not validator.validate_list(value, 1, max_value):
            dispatcher.utter_message(response="utter_did_not_understand")
            dispatcher.utter_message(response="utter_please_answer_1_to_5")
            return {"pa_doing_today_slot": None}

        return {"pa_doing_today_slot": value}

    def validate_pa_happened_special_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_happened_special_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)

        if last_utterance != 'utter_ask_pa_happened_special_slot':
            return {"pa_happened_special_slot": None}

        return {"pa_happened_special_slot": value}


class ValidatePaEnoughMotivationForm(FormValidationAction):
    def name(self) -> Text:
        return 'validate_pa_enough_motivation_form'

    def validate_pa_enough_motivation_slot(
            self, value: Text, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        # pylint: disable=unused-argument
        """Validate pa_enough_motivation_slot"""

        last_utterance = get_latest_bot_utterance(tracker.events)
        if last_utterance != 'utter_ask_pa_enough_motivation_slot':
            return {"pa_enough_motivation_slot": None}

        if not validator.validate_number_in_range_response(1, 2, value):
            dispatcher.utter_message(response="utter_please_answer_1_2")
            return {"pa_enough_motivation_slot": None}

        return {"pa_enough_motivation_slot": value}
