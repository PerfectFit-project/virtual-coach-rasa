from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
from state_machine.state import State

import logging


class DialogState:

    def __init__(self, running: bool, starting_time: datetime, current_dialog: str):
        self.running = running
        self.starting_time = starting_time
        self.current_dialog = current_dialog

    def set_to_running(self, dialog: str):
        """
        Set the dialog status to running
        Args:
            dialog: the name of the last started dialog

        """
        self.running = True
        self.starting_time = datetime.now()
        self.current_dialog = dialog

    def set_to_idle(self):

        """
        Set the dialog status to not running

        """
        self.running = False

    def get_current_dialog(self):

        """
        Get the current last running dialog

        """
        return self.current_dialog

    def get_running_status(self):

        """
        Get the current status of the dialog

        """
        return self.running

    def get_running_time(self):

        """
        Get the last time a dialog started

        """
        return self.starting_time


class EventEnum(Enum):
    DIALOG_COMPLETED = 'dialog_completed'
    DIALOG_RESCHEDULED = 'dialog_rescheduled'
    DIALOG_STARTED = 'dialog_started'
    NEW_DAY = 'new_day'
    USER_TRIGGER = 'user_trigger'


@dataclass
class Event:
    EventType: EventEnum
    Descriptor: Any


class StateMachine:

    def __init__(self, state: State, dialog_state: DialogState):
        self.state = state
        self.machine_id = self.state.user_id
        self.state.signal_new_event = self.new_state_callback
        self.dialog_state = dialog_state

        logging.info('A FSM has been created with the ID %s', self.machine_id)

    def on_event(self, event: Event):
        logging.info('Event received by FSM %s: ', event)

        if event.EventType == EventEnum.DIALOG_COMPLETED:
            logging.info('Dialog completed event received %s ', event.Descriptor)
            self.dialog_state.set_to_idle()
            self.state.on_dialog_completed(event.Descriptor)

        elif event.EventType == EventEnum.DIALOG_RESCHEDULED:
            logging.info('Dialog resheduled event received %s ', event.Descriptor)
            # in this case the descriptor is a tuple, where 0 is
            # the dialog and 1 the new date
            self.state.on_dialog_rescheduled(event.Descriptor[0], event.Descriptor[1])

        elif event.EventType == EventEnum.DIALOG_STARTED:
            logging.info('Dialog started event received %s ', event.Descriptor)
            # in this case we track that a dialog is running
            self.dialog_state.set_to_running(event.Descriptor)

        elif event.EventType == EventEnum.NEW_DAY:
            logging.info('New day received %s: ', event.Descriptor)
            # convert to date format
            event.Descriptor = self.descriptor_to_date(event.Descriptor)

            self.state.on_new_day(event.Descriptor)

        elif event.EventType == EventEnum.USER_TRIGGER:
            logging.info('User trigger event received %s ', event.Descriptor)
            self.dialog_state.set_to_running(event.Descriptor)
            self.state.on_user_trigger(event.Descriptor)

    def new_state_callback(self):
        self.state = self.state.new_state
        self.state.signal_new_event = self.new_state_callback

        logging.info('Moving to a new state %s: ', self.state.__state__())

        self.state.run()

    @staticmethod
    def descriptor_to_date(descriptor: Any):
        """
        Convert the date format provided in the descriptor to
        the date format
        Args:
            descriptor: the descriptor provided in the event

        Returns: the descriptor formatted as date

        """
        format_date = None

        if isinstance(descriptor, str):
            # get rid of milliseconds, in case they are present
            trimmed_date = descriptor.split('.')[0]
            try:
                format_date = datetime.strptime(trimmed_date, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                format_date = None

        elif isinstance(descriptor, date):
            format_date = descriptor

        return format_date
