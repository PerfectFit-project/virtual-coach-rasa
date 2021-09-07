[Celery](https://docs.celeryproject.org/en/stable/) is used to schedule tasks.

## How to run

### Before starting Celery, make sure you have started RASA:
```
# go to "Rasa_bot"

# start RASA action service
rasa run actions

# start RASA server
rasa run --enable-api
```

### Then you can start Celery as following:

```
# start redis store
docker run -d -p 6379:6379 redis

# start Celery worker with Celery Beat running in the background (in production you should run multiple workers)
celery --app=celery_tasks worker -B -l INFO
```
In the Celery worker terminal, you should see something like below:
```
[2021-09-07 15:01:33,526: INFO/MainProcess] Task celery_tasks.trigger_rasa_reminder[86a25632-3a01-4b2b-803b-9cc913866888] received
[2021-09-07 15:01:33,587: INFO/ForkPoolWorker-9] Task celery_tasks.trigger_rasa_reminder[86a25632-3a01-4b2b-803b-9cc913866888] succeeded in 0.06005297499999962s: None
```
which means the Celery works successfully!

So the Celery periodically sends a `EXTERNAL_set_reminder` intent to RASA to trigger RASA to set a reminder. This reminder will send a `EXTERNAL_utter_reminder` intent in 2 seconds (it's a setting just for development), and when RASA receives this intent, it will send the reminder message "Voorziet u vandaag risicovolle situaties voor het roken?" to user.


## How to check the reminder?

To see what you can get from the two intents `EXTERNAL_set_reminder` and `EXTERNAL_utter_reminder`, you can send them manually:

1. manually trigger RASA to set a reminder
```
curl -H "Content-Type: application/json" -X POST -d '{"name": "EXTERNAL_set_reminder"}' "http://localhost:5005/conversations/Kees/trigger_intent?output_channel=latest"
```
you should see a response like
```
{"tracker":{"sender_id":"Kees" ... "messages":[{"recipient_id":"Kees","text":"I will remind you in 2 seconds."}]}
```

2. manually trigger RASA to utter reminder message:
```
curl -H "Content-Type: application/json" -X POST -d '{"name": "EXTERNAL_utter_reminder"}' "http://localhost:5005/conversations/Kees/trigger_intent?output_channel=latest"
```
you should see a response like
```
{"tracker":{"sender_id":"Kees" ... "messages":[{"recipient_id":"Kees","text":"Voorziet u vandaag risicovolle situaties voor het roken?"}]}
```
