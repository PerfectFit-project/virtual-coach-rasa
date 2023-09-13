from celery import Celery
from rasa_sdk import Action
from rasa_sdk.events import SlotSet, FollowupAction
import datetime

from .helper import (dialog_to_be_completed,
                     get_current_user_phase,
                     get_dialog_completion_state,
                     get_goal_setting_chosen_sport_from_db)
from virtual_coach_db.helper.definitions import Components
from .definitions import REDIS_URL, FsmStates
from sensorapi.connector import get_steps_data

celery = Celery(broker=REDIS_URL)


class ActionTriggerRelapseDialog(Action):
    """Trigger the relapse the dialog"""

    def name(self):
        return "action_trigger_relapse_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        phase = get_current_user_phase(user_id)

        # check if the dialog can be executed (the use is in the execution phase)
        if phase != FsmStates.EXECUTION_RUN:
            return [FollowupAction('utter_help_not_available')]

        celery.send_task('celery_tasks.user_trigger_dialog',
                         (user_id, Components.RELAPSE_DIALOG))


class ActionTriggerFirstAidDialog(Action):
    """Trigger the first aid dialog"""

    def name(self):
        return "action_trigger_first_aid_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        ehbo_enabled = get_dialog_completion_state(user_id, Components.FIRST_AID_KIT_VIDEO)
        # if the first aid kit is available, trigger it
        if ehbo_enabled:
            celery.send_task('celery_tasks.user_trigger_dialog',
                             (user_id, Components.FIRST_AID_KIT))
        # if the first aid kit is not yet available, show the menu
        else:
            return[FollowupAction('utter_ehbo_not_available')]


class ActionTriggerExplainFirstAidVideoDialog(Action):
    """Trigger the first aid dialog explanation video"""

    def name(self):
        return "action_trigger_explanation_first_aid_video_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        ehbo_enabled = get_dialog_completion_state(user_id, Components.FIRST_AID_KIT_VIDEO)
        # if the first aid kit is available, trigger it
        if ehbo_enabled:
            celery.send_task('celery_tasks.user_trigger_dialog',
                             (user_id, Components.FIRST_AID_KIT_VIDEO))
        # if the first aid kit is not yet available, show the menu
        else:
            return [FollowupAction('utter_ehbo_not_available')]


class ActionTriggerGeneralActivityDialog(Action):
    """Trigger the general activity dialog"""

    def name(self):
        return "action_trigger_general_activity_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.GENERAL_ACTIVITY))


class ActionTriggerMedicineVideoDialog(Action):
    """Trigger the medicine video"""

    def name(self):
        return "action_trigger_video_medicine_dialog"

    async def run(self, dispatcher, tracker, domain):
        user_id = tracker.current_state()['sender_id']

        celery.send_task('celery_tasks.user_trigger_dialog', (user_id, Components.MEDICATION_TALK))


class ActionSelectMenu(Action):
    """Determines which list of commands has to be used"""

    def name(self):
        return "action_select_menu"

    async def run(self, dispatcher, tracker, domain):

        user_id = tracker.current_state()['sender_id']

        # is there a dialog to be completed
        complete_dialog = dialog_to_be_completed(user_id)
        # is the ehbo option to be shown (the explanatory video has been shown)
        show_ehbo = get_dialog_completion_state(user_id, Components.FIRST_AID_KIT_VIDEO)

        # is the doel option to be shown (the goal setting dialog has been shown)
        if get_goal_setting_chosen_sport_from_db(user_id) is not None:
            show_doel = True
        else:
            show_doel = False

        # the help command is shown just in the execution
        phase = get_current_user_phase(user_id)
        if phase != FsmStates.EXECUTION_RUN:
            show_help = False
        else:
            show_help = True

        # select the utterances

        # show the verder command
        if complete_dialog:
            dispatcher.utter_message(response="utter_central_mode_options_verder")
        # show the help command
        if show_help:
            dispatcher.utter_message(response="utter_central_mode_options_help")
        # show the ehbo command
        if show_ehbo:
            dispatcher.utter_message(response="utter_central_mode_options_ehbo")
        # show the exercise command
        dispatcher.utter_message(response="utter_central_mode_options_oefening")
        # show the medication video command
        dispatcher.utter_message(response="utter_central_mode_options_medicatie")
        # show the doel command
        if show_doel:
            dispatcher.utter_message(response="utter_central_mode_options_doel")
        # show the last general statement
        dispatcher.utter_message(response="utter_central_mode_options_outro")


class ActionTriggerUncompletedDialog(Action):
    """Trigger uncompleted dialog if there is one"""

    def name(self):
        return "action_trigger_uncompleted_dialog"

    async def run(self, dispatcher, tracker, domain):
        
        user_id = tracker.current_state()['sender_id']
        
        if dialog_to_be_completed(user_id):
            celery.send_task('celery_tasks.user_trigger_dialog',
                             (user_id, Components.CONTINUE_UNCOMPLETED_DIALOG))
        else:
            return [FollowupAction('utter_no_valid_uncompleted_dialog')]


class ActionIdleCommandsTodaySteps(Action):
    def name(self):
        return "action_idle_commands_today_steps"

    async def run(self, dispatcher, tracker, domain):
        # get smoking status with 1: not (re)lapsed and 2: did (re)lapse last 4 weeks

        user_id = int(tracker.current_state()['sender_id'])

        start = datetime.datetime.now()
        end = end_time + datetime.timedelta(days=1)

        # get number of steps from today
        steps_data = get_steps_data(user_id=user_id, start_date=start, end_date=end)
        today_steps = steps_data[0]['steps']

        return [SlotSet('idle_commands_today_steps', today_steps)]
