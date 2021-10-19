import requests
from celery import Celery

app = Celery('celery_tasks', broker='redis://redis:6379')

app.conf.beat_schedule = {
    'trigger_ask_foreseen_hrs': {
        'task': 'celery_tasks.trigger_ask_foreseen_hrs',
        'schedule': 120.0,
        'args': (),
    },
}


@app.task(bind=True)
def trigger_ask_foreseen_hrs(self):  # pylint: disable=unused-argument
    """Task to trigger RASA to set reminder for every user.
    """
    # TODO_db: get user IDs from database
    # TODO: add Celery or http error handling
    user_ids = ['38527']
    for user in user_ids:
        endpoint = f'http://rasa_server:5005/conversations/{user}/trigger_intent'
        headers = {'Content-Type': 'application/json'}
        params = {'output_channel': 'niceday_input_channel'}
        data = '{"name": "EXTERNAL_trigger_ask_foreseen_hrs"}'
        requests.post(endpoint, headers=headers, params=params, data=data)
