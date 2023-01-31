from dataclasses import dataclass
from enum import Enum
from state_machine.state import State
import logging


class EventEnum(Enum):
    USER_TRIGGER = 'user_trigger'
    DIALOG_COMPLETED = 'dialog_completed'
    NEW_DAy = 'new_day'


@dataclass
class Event:
    EventType: EventEnum
    Descriptor: any


class StateMachine:

    def __init__(self, state: State):
        self.state = state
        self.machine_id = self.state.user_id
        self.state.signal_new_event = self.new_state_callback
        logging.info('A FSM has been created with the ID ', self.machine_id)

    def on_event(self, event: Event):
        logging.info('Event received by FSM: ', event)
        if event.EventType == EventEnum.USER_TRIGGER:
            logging.info('User trigger event received %s ', event.Descriptor)
            self.state.on_user_trigger(event.Descriptor)
        elif event.EventType == EventEnum.DIALOG_COMPLETED:
            logging.info('Dialog completed event received %s ', event.Descriptor)
            self.state.on_dialog_completed(event.Descriptor)

    def new_state_callback(self):
        logging.info('I received a callback')
        self.state = self.state.new_state
        self.state.signal_new_event = self.new_state_callback
        logging.info('Moving to a new state %s: ', self.state.__state__())
        self.state.run()
