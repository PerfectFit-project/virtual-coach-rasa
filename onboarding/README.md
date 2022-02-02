# Instructions

## Build dependencies
`pip install -r requirements.txt`

If you get errors about `psycopg2` then this is probably because you have not installed postgres. If using homebrew you can e.g. `brew install postgresql` but in general it will depend on OS, package manager etc. Eventually this will all be running in a container anyway so the environment issue will be solved.

## Run the virtual coach system
Run the full application, see [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main). 

Currently, to make the onboarding script work with the main application, you need to make a change to the to the docker-compose.yml file in [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main). Make sure you add the niceday api port before running the application. This can be done by adding:
```
    ports:
      - "8080:8080"
```
_to the docker-compose.yml file in [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main)._


## Run with the (niceday) id of the user you wish to onboard
You can find your (niceday) id by inspecting the docker-compose console. Then run the onboarding script using:
`python onboarding.py 38527`

If there is already a user with this id then nothing will be added to the db.
You will get a message e.g.

`User 38527 already exists in the database.`
