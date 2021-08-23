import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rasa_scheduler.settings')

app = Celery('rasa_scheduler')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@app.task(bind=True)
def hello_world(self):
    print('Hello world!')

@app.task(bind=True)
def trigger_rasa_reminder(self):
    # TODO: send a rasa external_event

    print('Hello world!')