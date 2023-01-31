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
        self.new_state = None

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

    def __state__(self):

        return self.state

    def signal_new_event(self):
        """

        This function has to be called upon the transition to a new event.
        The state machine will receive this to update the state.

        """
        pass

    def set_new_state(self, new_state):
        self.new_state = new_state
        self.signal_new_event()


class StateEvent(object):

    def __init__(self):
        self.__eventhandlers = []

    def __iadd__(self, handler):
        self.__eventhandlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__eventhandlers.remove(handler)
        return self

    def __call__(self, *args, **keywargs):
        for eventhandler in self.__eventhandlers:
            eventhandler(*args, **keywargs)
