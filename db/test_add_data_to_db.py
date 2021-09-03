# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 14:54:18 2021

@author: bscheltinga
"""

from db.dbschema.models import Users
from db.helper import get_db_session

# Creat session object to connect db
session = get_db_session()

# Select right user (hard coded?)
ID = 1
selected = session.query(Users).filter_by(nicedayuid=ID).one()
print(selected.PA_evaluation)
selected.PA_evaluation = 4
session.commit()

# Commit/save the data to the db
# session.commit()
