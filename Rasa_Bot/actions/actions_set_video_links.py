from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from virtual_coach_db.helper.definitions import VideoLinks, Components


# set video links
class SetFakLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_fak_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.FIRST_AID_KIT)]


class SetFSLongVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_future_self_long_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.FUTURE_SELF_LONG)]


class SetFSShortVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_future_self_short_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.FUTURE_SELF_SHORT)]


class SetExecutionIntroductionVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_execution_introduction_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.INTRO_EXECUTION_VIDEO)]


class SetPreparationIntroductionVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_preparation_introduction_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.INTRO_PREPARATION_VIDEO)]


class SetMedicationVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_medication_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.MEDICATION_VIDEO)]


class SetTrackBehaviorVideoLink(Action):
    """ set the link to the medication video"""

    def name(self):
        return "action_set_track_behavior_video_link"

    async def run(self, dispatcher, tracker, domain):
        return [SlotSet("video_link",
                        VideoLinks.TRACKING_BEHAVIORS)]


# Set component slot

class SetSlotFakVideo(Action):
    def name(self):
        return "action_set_slot_first_aid_kit_video"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.FIRST_AID_KIT_VIDEO)]


class SetSlotFSLongVideo(Action):
    def name(self):
        return "action_set_slot_future_self_long"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.FUTURE_SELF_LONG)]


class SetSlotFSShortVideo(Action):
    def name(self):
        return "action_set_slot_future_self_short"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.FUTURE_SELF_LONG)]


class SetSlotExecutionIntroduction(Action):
    def name(self):
        return "action_set_slot_execution_introduction"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.EXECUTION_INTRODUCTION)]


class SetSlotPreparationIntroduction(Action):
    def name(self):
        return "action_set_slot_preparation_introduction"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.PREPARATION_INTRODUCTION)]


class SetSlotMedication(Action):
    def name(self):
        return "action_set_slot_medication_talk"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.MEDICATION_TALK)]


class SetSlotTrackBehavior(Action):
    def name(self):
        return "action_set_slot_track_behavior"

    async def run(self, dispatcher, tracker, domain):
        user_id = int(tracker.current_state()['sender_id'])  # retrieve userID

        return [SlotSet('current_intervention_component',
                        Components.TRACK_BEHAVIOR)]
