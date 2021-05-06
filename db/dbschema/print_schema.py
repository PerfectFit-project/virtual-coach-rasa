from sqlalchemy import create_engine
from sqlalchemy.engine import reflection

db_url = 'postgresql+psycopg2://root:root@db/perfectfit'

engine = create_engine(db_url)

print('Schema from', db_url, ':\n')
inspector = reflection.Inspector.from_engine(engine)
for table in inspector.get_table_names():
    print('Table', table, ':')
    for column in inspector.get_columns(table):
        print(column['name'], column['type'])
    print('')

