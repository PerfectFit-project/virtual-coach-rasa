from rasa_sdk import Action
from rasa_sdk.events import FollowupAction


class ActionEndDialog(Action):
    """Action to cleanly terminate the dialog."""
    # ATM this action just call the default restart action
    # but this can be used to perform actions that might be needed
    # at the end of each dialog
    def name(self):
        return "action_end_dialog"

    async def run(self, dispatcher, tracker, domain):

        return [FollowupAction('action_restart')]
