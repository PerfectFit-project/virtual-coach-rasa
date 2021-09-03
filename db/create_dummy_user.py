# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 14:34:59 2021
This script creates a dummy user, to b
"""

from db.dbschema.models import Users
from db.helper import get_db_session

# Open session with db
session = get_db_session()

# Add new user to the Users table
new_user = Users(
    nicedayuid=1,
    firstname= 'Kees',
    lastname= 'Jansen',
    location= 'Hengelo',
    gender='Male',
    dob= '03-09-2020'
)

session.add(new_user)
session.commit()