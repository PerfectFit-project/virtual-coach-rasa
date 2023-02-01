import datetime


class State(object):
    """
    Enum of possible states
    """

    ONBOARDING = "Onboarding"
    TRACKING = "Tracking"
    GOALS_SETTING = "Goals setting"
    BUFFER = "Buffer"
    EXECUTION_RUN = "Execution run"
    RELAPSE = "Relapse"
    CLOSING = "Closing"
    TEST = "Test"

    def __init__(self, user_id):
        """
        Initialize an instance of the state
        """
        self.user_id = user_id
        self.state = None
        self.new_state = None

    def __state__(self):

        return self.state

    def run(self):
        """
        Execute the actions when entering the state

        """
        pass

    def on_dialog_completed(self, dialog):
        """
        Determines what happens when a dialog has been completed
        Args:
            dialog: the dialog that started

        Returns:
            The new state to be activated, or None if the state is
            not to be changed
        """
        return None

    def on_user_trigger(self, dialog):
        """
        Determines what happens when a dialog is triggered by the user
        Args:
            dialog: the dialog triggered

        Returns:
            The new state to be activated, or None if the state is
            not to be changed

        """

        return None

    def on_new_day(self, date: datetime.date):
        """
        Determines what happens when on the date change. The timing might
        trigger a state transition
        Args:
            date: the current date

        """
        return None

    def signal_new_event(self):
        """

        This function has to be called upon the transition to a new event.
        The state machine will receive this to update the state.

        """
        pass

    def set_new_state(self, new_state):
        self.new_state = new_state
        self.signal_new_event()
