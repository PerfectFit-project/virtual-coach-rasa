import logging
import os
import requests
from celery import Celery
from celery.signals import worker_ready
from datetime import datetime, timedelta
from state_machine.state_machine import StateMachine, EventEnum, Event
from state_machine.const import REDIS_URL, TIMEZONE, MAXIMUM_DIALOG_DURATION
from state_machine.controller import OnboardingState
from state_machine.utils import get_component_name

app = Celery('celery_tasks', broker=REDIS_URL)

app.conf.enable_utc = True
app.conf.timezone = TIMEZONE

TEST_USER = int(os.getenv('TEST_USER_ID'))

state_machines = [{'machine': StateMachine(OnboardingState(TEST_USER)), 'id': TEST_USER}]


# state_machines = []

@worker_ready.connect
def at_start(sender, **k):  # pylint: disable=unused-argument
    """
    When celery is ready, the watchdog for the new day notification is started
    """
    notify_new_day.apply_async(args=[datetime.today()])


@app.task
def create_new_user(user_id: int):
    """
    This task creates a new StateMachine for the user specified.
    Args:
        user_id: the ID of the user
    """
    global state_machines

    state_machines.append({'machine': StateMachine(OnboardingState(user_id)), 'id': user_id})


@app.task
def start_user_intervention(user_id: int):
    """
    This task runs the first state of the StateMachine for a give user.
    Args:
        user_id: the ID of the user
    """
    user_fsm = next(item for item in state_machines if item['id'] == user_id)['machine']
    user_fsm.state.run()


@app.task(bind=True)
def user_trigger_dialog(self,  # pylint: disable=unused-argument
                        user_id: int,
                        intervention_component_name: str):
    """
    This task is used when a dialog is triggered by the user.
    Args:
        user_id: the ID of the user to send the trigger to
        intervention_component_name: the intent to be sent
    """
    send_fsm_event(user_id=user_id,
                   event=Event(EventEnum.USER_TRIGGER, intervention_component_name))


@app.task(bind=True)
def notify_new_day(self, current_date: datetime.date):  # pylint: disable=unused-argument
    """
    This task notifies all the state machines that a day has begun.
    Args:
        current_date: the date to be sent to the state machines
    """
    for item in state_machines:
        send_fsm_event(user_id=item['id'], event=Event(EventEnum.NEW_DAY, current_date))

    # schedule the task for tomorrow
    tomorrow = datetime.today() + timedelta(days=1)
    notify_new_day.apply_async(args=[tomorrow], eta=tomorrow)


@app.task(bind=True)
def intervention_component_completed(self,  # pylint: disable=unused-argument
                                     user_id: int,
                                     intervention_component_name: str):
    """
    This task notifies the state machine that a dialog has been rescheduled.
    Args:
        user_id: the ID of the user
        intervention_component_name: the component completed
    """

    logging.info('Celery received a dialog completion')
    send_fsm_event(user_id=user_id,
                   event=Event(EventEnum.DIALOG_COMPLETED, intervention_component_name))


@app.task
def reschedule_dialog(user_id: int, intervention_component_name: str, new_date: datetime):
    """
    This task notifies the state machine that a dialog has been rescheduled.
    Args:
        user_id: the ID of the user
        intervention_component_name: the component rescheduled
        new_date: the date to which the component has to be rescheduled
    """

    logging.info('Celery received a dialog rescheduling')
    send_fsm_event(user_id=user_id,
                   event=Event(EventEnum.DIALOG_RESCHEDULED,
                               (intervention_component_name, new_date)))


@app.task(bind=True)
def trigger_intervention_component(self, user_id, trigger):  # pylint: disable=unused-argument
    """
    This task sends a trigger to Rasa immediately.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
    """

    logging.info('Current machine state: %s', get_fsm(user_id).state.__state__())

    send_fsm_event(user_id, Event(EventEnum.DIALOG_STARTED, None))

    endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
    headers = {'Content-Type': 'application/json'}
    params = {'output_channel': 'niceday_trigger_input_channel'}
    data = '{"name": "' + trigger + '" }'
    requests.post(endpoint, headers=headers, params=params, data=data, timeout=60)


@app.task(bind=True)
def trigger_scheduled_intervention_component(self, user_id,  # pylint: disable=unused-argument
                                             trigger):
    """
    This task sends a trigger to Rasa after verifying that a dialog is not
    currently running for the user. If a dialog is running, it is rescheduled.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
    """

    user_fsm = get_fsm(user_id)
    # get the current fsm status
    status = user_fsm.dialog_state.get_running_status()
    last_time = user_fsm.dialog_state.get_running_time()

    now = datetime.now()

    # if a dialog is not running or the time has expired (Rasa session reset)
    # send the trigger

    logging.info("scheduled dialog trigger received")
    logging.info("FSM status: %s", status)
    logging.info("FSM time: %s", (now - last_time).seconds)
    logging.info("FSM id: %s", user_fsm.machine_id)

    if not status or (now - last_time).seconds > MAXIMUM_DIALOG_DURATION:
        user_fsm.dialog_state.set_to_running()
        trigger_intervention_component.apply_async(args=[user_id, trigger])

    else:
        # if a dialog is running, reschedule the trigger
        rescheduled_date = now + timedelta(minutes=MAXIMUM_DIALOG_DURATION)
        # retrieve the name of the component
        name = get_component_name(trigger)
        # send a rescheduling event
        send_fsm_event(user_id,
                       event=Event(EventEnum.DIALOG_RESCHEDULED, (name, rescheduled_date)))


def get_fsm(user_id: int) -> StateMachine:
    """
    Gets the StateMachine object of a user
    Args:
        user_id: ID of the user

    Returns: The StateMachine object of a user

    """
    user_fsm = next(item for item in state_machines if item['id'] == user_id)['machine']
    return user_fsm


def send_fsm_event(user_id: int, event: Event):
    """
    Send an event to the StateMachine of a user
    Args:
        user_id: ID of the user
        event: the event that need to be sent

    """
    user_fsm = get_fsm(user_id)
    user_fsm.on_event(event)
