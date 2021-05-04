# Set up the postgres database and management container
```
docker-compose up
```

# Applying migrations
```
docker-compose exec manage alembic upgrade head
```

# If database schema has changed
If the schema, defined using `SQLAlchemy` in `models.py` has changed, generate the new migration using:
```
docker-compose exec manage alembic revision --autogenerate
```

# Checking the tables of the currently running database
```
docker-compose exec manage python3 get_table_names.py
```
