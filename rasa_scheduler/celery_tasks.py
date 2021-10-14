import requests
from celery import Celery

app = Celery('celery_tasks',
             broker='redis://localhost:6379')

app.conf.beat_schedule = {
    'trigger-rasa-reminder': {
        'task': 'celery_tasks.trigger_rasa_reminder',
        'schedule': 60.0,
        'args': (),
    },
}


@app.task(bind=True)
def trigger_rasa_reminder(self):  # pylint: disable=unused-argument
    """Task to trigger RASA to set reminder for every user.
    """
    # TODO_db: get user IDs from database
    # TODO: add Celery or http error handling
    user_ids = ['38527']
    for user in user_ids:
        endpoint = f'http://localhost:5005/conversations/{user}/trigger_intent'
        headers = {'Content-Type': 'application/json'}
        params = {'output_channel': 'niceday_input_channel'}
        data = '{"name": "EXTERNAL_utter_reminder"}'
        requests.post(endpoint, headers=headers, params=params, data=data)
