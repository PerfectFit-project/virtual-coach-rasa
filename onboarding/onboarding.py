import argparse

from sqlalchemy import create_engine, MetaData

import sys
sys.path.insert(0, "../niceday_client/")

from niceday_client import NicedayClient

def onboard_user(userid):
    client = NicedayClient()

    print(f'Fetching niceday profile for user {userid}')
    profile = client.get_profile(userid)
    print('Profile:', profile)

    engine = create_engine('postgresql://root:root@localhost:5432/perfectfit', echo=False)
    meta = MetaData()
    meta.reflect(bind=engine)
    conn = engine.connect()

    new_user = {
        'nicedayuid': userid,
        'firstname': profile['firstName'],
        'lastname': profile['lastName'],
        'location': profile['location'],
        'gender': profile['gender'],
        'dob': profile['birthDate']
    }
    result = conn.execute(meta.tables['users'].insert().values(new_user))
    conn.close()

    print(result.inserted_primary_key)

def main(args=None):
    parser = argparse.ArgumentParser(description="Onboard the user with the given ID")
    parser.add_argument("userid", type=int, help="User ID on Sensehealth server")
    args = parser.parse_args()
    onboard_user(args.userid)

if __name__ == "__main__":
    main()
