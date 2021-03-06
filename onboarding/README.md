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
to [the `niceday-api` container in docker-compose.yml](https://github.com/PerfectFit-project/virtual-coach-main/blob/f96498de95729c415d5d3e530e661249bfadfd26/docker-compose.yml#L60). This will expose the niceday-api to localhost
Then, change [this line in onboarding.py](https://github.com/PerfectFit-project/virtual-coach-rasa/blob/4f7b65e644e8ede87d9b6379c6d81c978b532fce/onboarding/onboarding.py#L22) to `client = NicedayClient(niceday_api_uri="http://localhost:8080")`

## Run with the (niceday) id of the user you wish to onboard
You can find your (niceday) id by inspecting the docker-compose console. Then run the onboarding script using:
`python onboarding.py 38527`

If there is already a user with this id then nothing will be added to the db.
You will get a message e.g.

`User 38527 already exists in the database.`
