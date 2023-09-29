### StateMachine
The `StateMachine` class is defined in the 'state_machine.py' script. It is in charge of keeping track of the current intervention state. It also receive different types of events as defined in the 'Event' class, and decides which function of the state to activate depending on the event type. 
6 events have been defined:
- DIALOG_COMPLETED: a dialog has been completed in Rasa by the user. The completion is tracked and the logic to manage it is activated in the specific state
- DIALOG_RESCHEDULED: a dialog has been rescheduled. The specific state manages the actions to take
- DIALOG_STARTED: a dialog has started. The starting time and the event are tracked
- NEW_DAY: a new day has started. Some of the intervention states take different actions depending on the time dimension.
- USER_TRIGGER = a dialog has been triggered by the user in Rasa. The specific state manages the actions to be taken.

Each user is associated with the instance of a StateMachine.
The state machine is coupled with the `user_state_machine` table on the DB. Every time an event occurs, the state machine is populated with the data stored in the DB, the event is consumed, and the new parameters of the state machine are updated on the DB.

### Controller
In the `controller.py` each possible state is fully defined. Each state is an implementation of the abstract `State` class defined in `state.py`. Each state implements a different logic for managing the events sent by the StateMachine, and defines the rules for changing state.

### celery_tasks
In `celery_tasks.py` the possible celery tasks are defined and implemented. These tasks can be triggered both from Rasa and the states of the state machine. 
[Celery](https://docs.celeryproject.org/en/stable/) is used to schedule tasks.

## How to run
Start the main application, see instructions in [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main).

In the Docker output for the Celery worker, you should see something like below:
```
scheduler_1  | [2021-10-14 11:34:16,227: INFO/Beat] Scheduler: Sending due task celery_tasks.trigger_intervention_component (celery_tasks.trigger_rasa_reminder)
scheduler_1  | [2021-10-14 11:34:16,232: INFO/MainProcess] Task celery_tasks.trigger_intervention_component[f4c08d73-b866-4640-94be-503483c8e87d] received
scheduler_1  | [2021-10-14 11:34:16,400: INFO/ForkPoolWorker-2] Task celery_tasks.trigger_rasa_reminder[f4c08d73-b866-4640-94be-503483c8e87d] succeeded in 0.16701790000661276s: None
```
which means Celery works successfully!
