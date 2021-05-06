from sqlalchemy import create_engine

engine = create_engine('postgresql+psycopg2://root:root@db/perfectfit')
print(engine.table_names())
