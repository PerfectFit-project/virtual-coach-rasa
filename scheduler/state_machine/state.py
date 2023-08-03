import datetime
from celery import Celery
from .const import RESCHEDULE_DIALOG


class State:
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
    COMPLETED = "Completed"

    def __init__(self, user_id, celery: Celery):
        """
        Initialize an instance of the state
        """
        self.user_id = user_id
        self.state = None
        self.new_state = None
        self.celery = celery

    def __state__(self):

        return self.state

    def run(self):
        """
        Execute the actions when entering the state

        """

    def on_dialog_completed(self, dialog):  # pylint: disable=unused-argument
        """
        Determines what happens when a dialog has been completed
        Args:
            dialog: the dialog that started

        """
        return None

    def on_dialog_expired(self, dialog):
        """
        Determines what happens when a dialog expired. if not overwritten,
        it reschedules the dialog for the day after.
        Args:
            dialog: the dialog that expired

        """
        next_day = datetime.datetime.now() + datetime.timedelta(days=1)

        self.celery.send_task(RESCHEDULE_DIALOG,
                              (self.user_id,
                               dialog,
                               next_day))

    def on_dialog_rescheduled(self, dialog, new_date):  # pylint: disable=unused-argument
        """
        Determines what happens when a dialog is rescheduled
        Args:
            dialog: the dialog that rescheduled
            new_date: rescheduled date

        """
        return None

    def on_user_trigger(self, dialog):  # pylint: disable=unused-argument
        """
        Determines what happens when a dialog is triggered by the user
        Args:
            dialog: the dialog triggered


        """

        return None

    def on_new_day(self, current_date: datetime.date):  # pylint: disable=unused-argument
        """
        Determines what happens when on the date change. The timing might
        trigger a state transition
        Args:
            current_date: the current date

        """
        return None

    def signal_new_event(self):
        """

        This function has to be called upon the transition to a new event.
        The state machine will receive this to update the state.

        """

    def set_new_state(self, new_state):
        self.new_state = new_state
        self.signal_new_event()
