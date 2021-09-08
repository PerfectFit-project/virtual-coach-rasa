# Set up the postgres database and management container.
Run the following in the directory that contains the `docker-compose.yml` file:
```
docker-compose up
```

# Applying migrations
You must deliberately apply existing migrations:
```
docker-compose exec manage alembic upgrade head
```

# If you want to change the database schema

## 1. Edit `models.py`
The schema is defined using `SQLAlchemy` in the `dbschema/models.py` file. You can edit this file to
describe the new database structure you want.

## 2. Generate the revision to the new schema

First make sure that all current migrations have been applied:
```
docker-compose exec manage alembic upgrade head
```

Then generate the revision to upgrade to the new schema defined in `models.py`:
```
docker-compose exec manage alembic revision --autogenerate
```

## 3. Apply the new revision

Finally, apply migrations again to upgrade to the latest revision:
```
docker-compose exec manage alembic upgrade head
```

If you want this revision to be permanent and available to others, please
remember to `git add` it to the repo. It will be found in the `dbschema/migrations/versions/`
directory. Use `git status` to see which files in there are new.


# Checking the schema of the currently running database
You can use the running `manage` container to execute other checks on the
postgres db. For example, you can print out the database metadata:
```
docker-compose exec manage python3 print_schema.py
```
