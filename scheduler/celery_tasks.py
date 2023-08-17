import logging
import time

import requests
from celery import Celery
from celery.schedules import crontab
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from state_machine.state import State
from state_machine.state_machine import EventEnum, Event
from state_machine.const import (REDIS_URL, TIMEZONE, MAXIMUM_DIALOG_DURATION, NICEDAY_API_ENDPOINT,
                                 RUNNING, EXPIRED, NOTIFY, INVITES_CHECK_INTERVAL,
                                 MAXIMUM_INACTIVE_DAYS, MORNING_TIME, WORDS_PER_SECOND, MAX_DELAY)
from typing import Optional
from celery_utils import (check_if_physical_relapse, check_if_task_executed, check_if_user_active,
                          check_if_user_exists, create_new_user, get_component_name, get_user_fsm,
                          get_dialog_state, get_all_fsm, get_scheduled_task_from_db,
                          save_state_machine_to_db, send_fsm_event, set_dialog_running_status,
                          update_scheduled_task_db, update_task_uuid_db)
from virtual_coach_db.helper.definitions import (NotificationsTriggers, ComponentsTriggers,
                                                 Components)


from niceday_client import NicedayClient

app = Celery('celery_tasks', broker=REDIS_URL)
app.conf.enable_utc = True
app.conf.timezone = TIMEZONE
# 1 month visibility. Temporary fix
app.conf.broker_transport_options = {'visibility_timeout': 2678400}

client = NicedayClient(niceday_api_uri=NICEDAY_API_ENDPOINT)

# Django configuration for cache memory usage
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
settings.configure(CACHES=CACHES)

LOCK_EXPIRE = 30


@contextmanager
def memcache_lock(lock_id, oid):
    status = cache.add(lock_id, oid)
    try:
        yield status
    finally:
        if status:
            cache.delete(lock_id)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):  # pylint: disable=unused-argument
    """
    When celery is ready, the watchdogs for the new day notification
    and for the dialogs status check are started
    """
    # notify the FSM that a new day started
    sender.add_periodic_task(crontab(hour=MORNING_TIME, minute=00), notify_new_day.s())
    # check if the user is active and send notification
    sender.add_periodic_task(crontab(hour=10, minute=00), check_inactivity.s())
    # check if the user is in physical relapse
    # sender.add_periodic_task(crontab(hour=10, minute=00), check_physical_relapse.s())
    # check if a dialog has been completed
    sender.add_periodic_task(MAXIMUM_DIALOG_DURATION, check_dialogs_status.s())
    # check if new connections are pending and, in case, accept them
    sender.add_periodic_task(INVITES_CHECK_INTERVAL, check_new_connection_request.s())
    # check if there are tasks pending and cancelled from the scheduler queue
    restore_scheduled_tasks.apply_async(eta=datetime.now() + timedelta(minutes=1))


@app.task
def restore_scheduled_tasks():
    # get all the already scheduled tasks
    scheduled_task = app.control.inspect().scheduled()
    tasks_list = [task['request']['id']
                  for workers in scheduled_task
                  for task in scheduled_task[workers]]

    # get all the tasks scheduled in the DB
    db_tasks = get_scheduled_task_from_db()

    # restore the tasks that were scheduled in the DB but are no more in the tasks list
    for db_task in db_tasks:
        # if the tasks saved in the DB is not in the list of the scheduled tasks
        if db_task.task_uuid not in tasks_list:
            # reschedule the task
            new_task = trigger_scheduled_intervention_component.apply_async(
                args=[db_task.users_nicedayuid,
                      db_task.intervention_component.intervention_component_trigger],
                eta=db_task.next_planned_date.astimezone(TIMEZONE))

            # update the uuid in the DB
            update_task_uuid_db(old_uuid=db_task.task_uuid, new_uuid=str(new_task.task_id))


@app.task
def check_physical_relapse():
    """
    This tasks checks if the user has fallen into a physical activity relapse state and,
    in this case, triggers the correspondent dialog
    """

    range_start = date.today()

    state_machines = get_all_fsm()

    for fsm in state_machines:
        user_id = fsm.machine_id
        if fsm.dialog_state == State.EXECUTION_RUN:
            relapse = check_if_physical_relapse(user_id, range_start)

            if relapse:
                current_dialog_state = get_dialog_state(fsm)
                if current_dialog_state == RUNNING:
                    new_time = datetime.now() + timedelta(seconds=MAXIMUM_DIALOG_DURATION)
                    reschedule_dialog.apply_async(
                        args=[user_id, Components.RELAPSE_DIALOG_SYSTEM, new_time])

                trigger_intervention_component.apply_async(
                    args=[user_id, ComponentsTriggers.RELAPSE_DIALOG_SYSTEM])


@app.task(bind=True)
def check_new_connection_request(self):
    """
    This tasks checks if there are pending connection requests and, in case there are,
    accepts them and creates a new user in the db.
    """

    lock_id = f'{self.name}-lock'
    with memcache_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            logging.info('checking new connections')

            pending_requests = client.get_invitation_requests()

            for request in pending_requests:
                user_id = request['id']
                user_exists = check_if_user_exists(user_id)
                # the request is accepted only if the user is not yet registered.
                # The users will be disconnected from the VC at the end of the intervention, and
                # it should not be possible to re-connect
                if not user_exists:
                    client.accept_invitation_request(str(request['invitationId']))
                    create_new_user(user_id)
                    start_user_intervention(user_id)


@app.task(bind=True)
def check_dialogs_status(self):  # pylint: disable=unused-argument
    """
    This task verifies if there are uncompleted dialogs and, in case, reschedules them.
    The task is rescheduled every maximum duration of the dialog time
    """

    # this check should not run between 23 and 7
    current_date = datetime.now(tz=TIMEZONE)

    if 0 < current_date.hour < MORNING_TIME:
        return

    logging.info("Checking the dialogs status")

    state_machines = get_all_fsm()

    for fsm in state_machines:
        dialog_state = get_dialog_state(fsm)
        dialog = fsm.dialog_state.get_current_dialog()
        logging.info(f"User {fsm.machine_id} current dialog state {dialog_state}")

        if dialog_state == NOTIFY:
            trigger_intent.apply_async(args=[fsm.machine_id,
                                             NotificationsTriggers.FINISH_DIALOG_NOTIFICATION])

        if dialog_state == EXPIRED:

            # the dialog is idle now
            fsm.dialog_state.set_to_idle()
            save_state_machine_to_db(fsm)

            send_fsm_event(user_id=fsm.machine_id,
                           event=Event(EventEnum.DIALOG_EXPIRED, dialog))


@app.task
def check_inactivity():
    """
    This task checks for all the users if they have been inactive for at least 10 days.
    If they have been inactive, the correspondent notification is sent
    Args:
    """
    current_date = date.today()
    state_machines = get_all_fsm()
    for item in state_machines:
        if not check_if_user_active(item.machine_id, current_date, MAXIMUM_INACTIVE_DAYS):
            current_dialog_state = get_dialog_state(item)
            if current_dialog_state == RUNNING:
                return
            trigger_intent.apply_async(args=[item.machine_id,
                                             NotificationsTriggers.INACTIVE_USER_NOTIFICATION])


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
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


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def notify_new_day(self, current_date: Optional[date] = None):  # pylint: disable=unused-argument
    """
    This task notifies all the state machines that a day has begun.
    Args:
        current_date: the date to be sent to the state machines. If None, uses the current date
    """
    if current_date is None:
        current_date = date.today()

    state_machines = get_all_fsm()
    for item in state_machines:
        send_fsm_event(user_id=item.machine_id, event=Event(EventEnum.NEW_DAY, current_date))


@app.task(autoretry_for=(Exception,), retry_backoff=True)
def reschedule_dialog(user_id: int, intervention_component_name: str, new_date: datetime):
    """
    This task notifies the state machine that a dialog has been rescheduled.
    Args:
        user_id: the ID of the user
        intervention_component_name: the component rescheduled
        new_date: the date to which the component has to be rescheduled
    """

    logging.info('Celery received a dialog rescheduling')

    # check if the scheduled time is in the night (i.e., after midnight and before 6)
    # In case it is, reschedule for the morning.
    if 0 <= new_date.hour <= MORNING_TIME:
        new_date.replace(hour=8)

    send_fsm_event(user_id=user_id,
                   event=Event(EventEnum.DIALOG_RESCHEDULED_USER,
                               (intervention_component_name, new_date.astimezone(TIMEZONE))))


@app.task(autoretry_for=(Exception,), retry_backoff=True)
def start_user_intervention(user_id: int):
    """
    This task runs the first state of the StateMachine for a give user.
    Args:
        user_id: the ID of the user
    """

    user_fsm = get_user_fsm(user_id)
    user_fsm.state.run()


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def trigger_intervention_component(self,  # pylint: disable=unused-argument
                                   user_id: int,
                                   trigger: str):
    """
    This task sends a trigger to Rasa immediately.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
    """
    response_intent = send_trigger(user_id, trigger)

    if response_intent == 200:
        # if the request succeeded, update the fsm
        name = get_component_name(trigger)
        send_fsm_event(user_id, Event(EventEnum.DIALOG_STARTED, name))
    else:
        logging.info('Exception during trigger_intervention_component')
        raise Exception()


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def trigger_scheduled_intervention_component(self,
                                             user_id: int,
                                             trigger: str):
    """
    This task sends a trigger to Rasa after verifying that a dialog is not
    currently running for the user. If a dialog is running, it is rescheduled.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
    """

    # check if the scheduled dialog has been already completed by the user
    # in case it has already been completed, do not execute
    if check_if_task_executed(self.request.id):
        return

    user_fsm = get_user_fsm(user_id)

    dialog_state = get_dialog_state(user_fsm)

    # retrieve the name of the component
    name = get_component_name(trigger)

    # check if the current time is in the night (i.e., after midnight and before 6)
    # In case it is, reschedule for the morning.
    current_date = datetime.now(tz=TIMEZONE)
    if 0 <= current_date.hour <= 7:
        current_date.replace(hour=8)
        send_fsm_event(user_id,
                       event=Event(EventEnum.DIALOG_RESCHEDULED_AUTO, (name, current_date)))

        return

    # if a dialog is not running or the time has expired (Rasa session reset)
    # send the trigger
    if dialog_state != RUNNING:
        user_fsm.dialog_state.set_to_running(dialog=name)
        #TODO: update last_time field
        trigger_intervention_component.apply_async(args=[user_id, trigger])
        update_scheduled_task_db(user_id, self.request.id)

    else:
        # if a dialog is running, reschedule the trigger
        rescheduled_date = datetime.now() + timedelta(seconds=MAXIMUM_DIALOG_DURATION)
        # send a rescheduling event
        send_fsm_event(user_id,
                       event=Event(EventEnum.DIALOG_RESCHEDULED_AUTO, (name, rescheduled_date)))


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
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


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def trigger_intent(self,  # pylint: disable=unused-argument
                   user_id: int,
                   trigger: str,
                   dialog_status: bool = None):
    """
    This task sends a trigger to Rasa immediately.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
        dialog_status: set the dialog state in the fsm
    """

    logging.info(f'Received trigger_intent task with {trigger} trigger for user {user_id}')

    response_intent = send_trigger(user_id, trigger)

    if response_intent != 200:
        logging.info('Exception during trigger_intent')
        raise Exception()

    if dialog_status is not None:
        # the state machine status as to be marked as not running
        # to allow new dialogs to be administered
        set_dialog_running_status(user_id, dialog_status)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def pause_conversation(self,  # pylint: disable=unused-argument
                       user_id: int):
    """
    This task sends a pause event to rasa to pause the current dialog.
    Args:
        user_id: the ID of the user to send the trigger to
    """
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/tracker/events'
    headers = {'Content-Type': 'application/json'}
    data = '[{"event": "pause"}]'
    response = requests.post(endpoint, headers=headers, data=data, timeout=60)

    if response.status_code != 200:
        logging.info('Exception during pause_conversation')
        raise Exception()


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def pause_and_resume(self,  # pylint: disable=unused-argument
                     user_id: int,
                     time: datetime,
                     dialog_status: bool = None):
    """
    This task sends a pause the dialog and schedules the resume.
    Args:
        user_id: the ID of the user to send the trigger to
        time: time for scheduling the dialog resume
        dialog_status: set the dialog state in the fsm after resuming
    """
    pause_conversation.apply_async(args=[user_id])
    resume.apply_async(args=[user_id, dialog_status], eta=time)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def pause_and_trigger(self,  # pylint: disable=unused-argument
                      user_id: int,
                      trigger: str,
                      time: datetime,
                      acknowledge: bool = False):
    """
    This task sends a pause the dialog and schedules the resume.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent
        time: time for scheduling the dialog resume
        acknowledge: if true, use the trigger_intervention_component task, to acknowledge the FSM.
        When the FSM in acknowledged, the trigger will result in the full process of starting a new
        dialog, so new entry is added to the DB and the starting time of the dialog is updated.
    """
    pause_conversation.apply_async(args=[user_id])
    resume_and_trigger.apply_async(args=[user_id, trigger, acknowledge], eta=time)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def resume(self,  # pylint: disable=unused-argument
           user_id: int,
           dialog_status: bool = None):
    """
    This task sends a resume event to Rasa.
    Args:
        user_id: the ID of the user to send the trigger to
        dialog_status: set the dialog state in the fsm
    """
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/tracker/events'
    headers = {'Content-Type': 'application/json'}
    data = '[{"event": "resume"}]'
    response = requests.post(endpoint, headers=headers, data=data, timeout=60)

    if response.status_code != 200:
        logging.info('Exception during resume')
        raise Exception()

    if dialog_status is not None:
        # the state machine status as to be marked as not running
        # to allow new dialogs to be administered
        set_dialog_running_status(user_id, dialog_status)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def resume_and_trigger(self,  # pylint: disable=unused-argument
                       user_id: int,
                       trigger: str,
                       acknowledge: bool = False):
    """
    This task sends a resume event to Rasa and triggers a new intent.
    Args:
        user_id: the ID of the user to send the trigger to
        trigger: the intent to be sent after the dialog is resumed
        acknowledge: if true, use the trigger_intervention_component task, to acknowledge the FSM
    """
    endpoint = f'http://rasa_server:5005/conversations/{user_id}/tracker/events'
    headers = {'Content-Type': 'application/json'}
    data = '[{"event": "resume"}]'
    response_resume = requests.post(endpoint, headers=headers, data=data, timeout=60)

    if response_resume.status_code != 200:
        raise Exception()

    if acknowledge:
        trigger_intervention_component.apply_async(
            args=[user_id, trigger])

    else:
        response_intent = send_trigger(user_id, trigger)
        if response_intent != 200:
            logging.info('Exception during resume_and_trigger')
            raise Exception()


def send_trigger(user_id: int, trigger: str):
    """
    Prepare and send the HTTP post request to rasa for triggering an intent.
    Args:
        user_id: ID of the user to whom the intent has to be sent
        trigger: Intent trigger

    Returns:

    """

    logging.info(f'received send_trigger tasks with {trigger} for {user_id}')

    endpoint = f'http://rasa_server:5005/conversations/{user_id}/trigger_intent'
    headers = {'Content-Type': 'application/json'}
    params = {'output_channel': 'latest'}
    data = '{"name": "' + trigger + '" }'

    response_intent = requests.post(endpoint, headers=headers, params=params, data=data, timeout=60)

    res_json = response_intent.json()

    for mes in res_json['messages']:
        recipient_id = mes['recipient_id']
        message = mes['text']
        client.post_message(int(recipient_id), message)

        delay = len(message.split(' ')) / WORDS_PER_SECOND
        delay = min(delay, MAX_DELAY)
        time.sleep(delay)

    return response_intent.status_code
