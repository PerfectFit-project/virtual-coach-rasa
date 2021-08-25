import argparse

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

import sys

sys.path.insert(0, "../niceday_client/")
from niceday_client import NicedayClient

sys.path.insert(0, "../db/dbschema/")
from models import Base, Users

def onboard_user(userid):
    client = NicedayClient()

    print(f'Fetching niceday profile for user {userid}')
    profile = client.get_profile(userid)
    print('Profile:', profile)

    engine = create_engine('postgresql://root:root@localhost:5432/perfectfit', echo=False)
    meta = MetaData()
    meta.reflect(bind=engine)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()

    # Check if this user already exists in the table
    # (assumes niceday user id is unique and immutable)
    existing_users = session.query(Users).filter(Users.nicedayuid == userid).count()
    if existing_users != 0:
        sys.exit(f'User {userid} already exists in the database.')

    # Add new user to the Users table
    new_user = Users (
        nicedayuid = userid,
        firstname = profile['firstName'],
        lastname = profile['lastName'],
        location = profile['location'],
        gender = profile['gender'],
        dob = profile['birthDate']
    )

    session.add(new_user)
    session.commit()

def main(args=None):
    parser = argparse.ArgumentParser(description="Onboard the user with the given ID")
    parser.add_argument("userid", type=int, help="User ID on Sensehealth server")
    args = parser.parse_args()
    onboard_user(args.userid)

if __name__ == "__main__":
    main()
