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
        logging.info('A FSM has been created with the ID ', self.machine_id)

    def on_event(self, event: Event):
        logging.info('Event received by FSM: ', event)
        new_state = None
        if event.EventType == EventEnum.USER_TRIGGER:
            logging.info('User trigger event received', event.EventType)
            new_state = self.state.on_user_trigger(event.Descriptor)
        elif event.EventType == EventEnum.DIALOG_COMPLETED:
            logging.info('Dialog completed event received', event.Descriptor)
            new_state = self.state.on_dialog_completed(event.Descriptor)

        if new_state is not None:
            self.state = new_state
            new_state.run()
