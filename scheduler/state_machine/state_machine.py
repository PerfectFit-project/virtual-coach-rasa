from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any

from state_machine.state import State
import logging


class EventEnum(Enum):
    DIALOG_COMPLETED = 'dialog_completed'
    DIALOG_RESCHEDULED = 'dialog_rescheduled'
    NEW_DAY = 'new_day'
    USER_TRIGGER = 'user_trigger'


@dataclass
class Event:
    EventType: EventEnum
    Descriptor: any


class StateMachine:

    def __init__(self, state: State):
        self.state = state
        self.machine_id = self.state.user_id
        self.state.signal_new_event = self.new_state_callback

        logging.info('A FSM has been created with the ID %s', self.machine_id)

    def on_event(self, event: Event):
        logging.info('Event received by FSM %s: ', event)

        if event.EventType == EventEnum.DIALOG_COMPLETED:
            logging.info('Dialog completed event received %s ', event.Descriptor)
            self.state.on_dialog_completed(event.Descriptor)

        if event.EventType == EventEnum.DIALOG_RESCHEDULED:
            logging.info('Dialog completed event received %s ', event.Descriptor)
            # in this case the descriptor is a tuple, where 0 is
            # the dialog and 1 the new date
            self.state.on_dialog_rescheduled(event.Descriptor[0], event.Descriptor[1])

        elif event.EventType == EventEnum.NEW_DAY:
            logging.info('New day received %s: ', event.Descriptor)
            # convert to date format
            event.Descriptor = self.descriptor_to_date(event.Descriptor)

            self.state.on_new_day(event.Descriptor)

        if event.EventType == EventEnum.USER_TRIGGER:
            logging.info('User trigger event received %s ', event.Descriptor)
            self.state.on_user_trigger(event.Descriptor)

    def new_state_callback(self):
        logging.info('I received a callback')

        self.state = self.state.new_state
        self.state.signal_new_event = self.new_state_callback

        logging.info('Moving to a new state %s: ', self.state.__state__())

        self.state.run()

    @staticmethod
    def descriptor_to_date(descriptor: Any) -> date:
        """
        Convert the date format provided in the descriptor to
        the date format
        Args:
            descriptor: the descriptor provided in the event

        Returns: the descriptor formatted as date

        """
        if type(descriptor) == str:
            try:
                format_date = datetime.strptime(descriptor, '%Y-%m-%dT%H:%M:%S').date()
            except:
                format_date = descriptor

        else:
            format_date = descriptor

        return format_date
