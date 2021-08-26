import os
import requests
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rasa_scheduler.settings')

app = Celery('rasa_scheduler')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def trigger_rasa_reminder(self):  # pylint: disable=unused-argument
    """Task to trigger RASA to set reminder for every user.
    """
    # TODO: get user IDs from database
    # TODO: add Celery error handling
    user_ids = ['Kees', ]
    for user in user_ids:
        endpoint = f'http://localhost:5005/conversations/{user}/trigger_intent'
        headers = {'Content-Type': 'application/json'}
        params = {'output_channel': 'latest'}
        data = '{"name": "EXTERNAL_set_reminder"}'
        requests.post(endpoint, headers=headers, params=params, data=data)
