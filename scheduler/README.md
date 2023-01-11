[Celery](https://docs.celeryproject.org/en/stable/) is used to schedule tasks.

## How to run
Start the main application, see instructions in [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main).

In the Docker output for the Celery worker, you should see something like below:
```
scheduler_1  | [2021-10-14 11:34:16,227: INFO/Beat] Scheduler: Sending due task trigger-rasa-reminder (celery_tasks.trigger_rasa_reminder)
scheduler_1  | [2021-10-14 11:34:16,232: INFO/MainProcess] Task celery_tasks.trigger_rasa_reminder[f4c08d73-b866-4640-94be-503483c8e87d] received
niceday_api_1     | POST /messages/ 200 0.982 ms - -
scheduler_1  | [2021-10-14 11:34:16,400: INFO/ForkPoolWorker-2] Task celery_tasks.trigger_rasa_reminder[f4c08d73-b866-4640-94be-503483c8e87d] succeeded in 0.16701790000661276s: None
```
which means Celery works successfully!

So Celery periodically sends a `EXTERNAL_trigger_ask_foreseen_hrs` intent to RASA to trigger RASA to utter `ask_foreseen_hrs` to user.


## How to manually trigger RASA?
Manually trigger RASA to start foreseen HRS conversation
```
curl --location --request POST 'http://localhost:5005/conversations/38527/trigger_intent?output_channel=niceday_trigger_input_channel' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "EXTERNAL_trigger_ask_foreseen_hrs"
}'
```
You should see a big json response with something like this in it:
```
{"tracker":{"sender_id":"Kees" ... 
            "latest_message": {
                "intent": {
                    "name": "EXTERNAL_trigger_ask_foreseen_hrs"
                },}]}
```
