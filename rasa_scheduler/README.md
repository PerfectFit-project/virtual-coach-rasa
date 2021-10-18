[Celery](https://docs.celeryproject.org/en/stable/) is used to schedule tasks.

## How to run

### Start the main application
Before starting Celery, make sure you have started the main application. 
Run `script/server` in the root of this repo.


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

So the Celery periodically sends a `EXTERNAL_utter_reminder` intent to RASA to trigger RASA to utter "Voorziet u vandaag risicovolle situaties voor het roken?" to user.


## How to check the reminder?

Manually trigger RASA to utter reminder message:
```
curl --location --request POST 'http://localhost:5005/conversations/38527/trigger_intent?output_channel=niceday_input_channel' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "EXTERNAL_utter_reminder"
}'
```
you should see a response like
```
{"tracker":{"sender_id":"Kees" ... "messages":[{"recipient_id":"Kees","text":"Voorziet u vandaag risicovolle situaties voor het roken?"}]}
```
