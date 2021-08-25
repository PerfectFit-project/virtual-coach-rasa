[Celery](https://docs.celeryproject.org/en/stable/) is used to schedule tasks. [Django-celery-beat](https://django-celery-beat.readthedocs.io/en/latest/) is used for storing and managing periodic tasks.

# How to run

1. Create Django super user
`python manage.py createsuperuser`

2. Start the Django admin
`python manage.py runserver`

3. Go to Django admin interface (http://127.0.0.1:8000/admin/) and login
 with the user and password created in step 1

4. Manage periodic tasks in Django amdin, e.g. add, delete or edit tasks.
Then you can log out the admin.

5. Start Celery

```
# start redis store
docker run -d -p 6379:6379 redis

# start Celery beat
celery -A rasa_scheduler beat -l INFO

# start Celery worker
celery -A rasa_scheduler worker -l INFO
```

Then you can see the running like "XXXX"


===============================

Before start celery, make sure you start the RASA

Go to "rasa_bot"
run `rasa run actions`
run `rasa run --enable-api`

try the commands:

`curl -H "Content-Type: application/json" -X POST -d '{"name": "EXTERNAL_utter_reminder"}' "http://localhost:5005/conversations/SSS/trigger_intent?output_channel=latest"`
you should get a response like "XXXX"

`curl -H "Content-Type: application/json" -X POST -d '{"name": "EXTERNAL_utter_reminder"}' "http://localhost:5005/conversations/SSS/trigger_intent?output_channel=latest"`
you should get a response like "XXXX"