# Instructions

## Build dependencies
`pip install -r requirements.txt`

If you get errors about `psycopg2` then this is probably because you have not installed postgres. If using homebrew you can e.g. `brew install postgresql` but in general it will depend on OS, package manager etc. Eventually this will all be running in a container anyway so the environment issue will be solved.

## Run the virtual coach system
Run the full application, see [virtual-coach-main](https://github.com/PerfectFit-project/virtual-coach-main)

## Run with the (niceday) id of the user you wish to onboard
`python onboarding.py 38527`

If there is already a user with this id then nothing will be added to the db.
You will get a message e.g.
`User 38527 already exists in the database.`
