class State(object):
    """
    Enum of possible states
    """

    ONBOARDING = "Onboarding"
    TRACKING = "Tracking"
    GOALS_SETTING = "Goals setting"
    BUFFER = "Buffer"
    EXECUTION_START = "Execution start"
    EXECUTION_RUN = "Execution run"
    RELAPSE = "Relapse"
    CLOSING = "Closing"
    TEST = "Test"

    def __init__(self):
        """
        Initialize an instance of the state
        """
        self.state = None
        self.user_id = None

    def run(self):
        """
        Execute the actions when entering the state

        """
        pass

    def on_event(self, event):
        """
        Logic to decide which is the next state
        Args:
            event:  event that triggers the transition

        Returns:

        """
        pass

    def on_dialog_completed(self, dialog):
        """
        Determines what happens when a dialog has been completed
        Args:
            dialog: the dialog that started

        Returns:

        """
        pass

    def on_user_trigger(self, dialog):
        """
        Determines what happens when a dialog is triggered by the user
        Args:
            dialog: the dialog triggered

        Returns:

        """
        pass

    def __state__(self):

        return self.state
