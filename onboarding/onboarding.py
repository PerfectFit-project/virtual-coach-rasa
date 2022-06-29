import argparse
import sys

from virtual_coach_db.dbschema.models import Users
from virtual_coach_db.helper.helper_functions import get_db_session
from niceday_client import NicedayClient, TrackerStatus
from niceday_client.definitions import Tracker


def enable_custom_trackers(userid: int):
    """
    Enable custom trackers for user. We enable:
     - 'tracker_smoking', trackerId=Tracker.SMOKING

    See https://github.com/senseobservationsystems/goalie-js/issues/840 on how to get a
    trackerId for a certain custom tracker.

    Args:
        userid: ID of the user you want to set tracker status for
    """
    print('Enabling custom trackers')
    client = NicedayClient()
    client.set_user_tracker_statuses(
        userid,
        [TrackerStatus(trackerId=Tracker.SMOKING, isEnabled=True)])


def onboard_user(userid):
    client = NicedayClient()
    enable_custom_trackers(userid)
    print(f'Fetching niceday profile for user {userid}')
    profile = client.get_profile(userid)
    print('Profile:', profile)

    # Open session with db
    session = get_db_session()

    # Check if this user already exists in the table
    # (assumes niceday user id is unique and immutable)
    existing_users = (session.query(Users).
                      filter(Users.nicedayuid == userid).
                      count())
    if existing_users != 0:
        sys.exit(f'User {userid} already exists in the database.')

    # Add new user to the Users table
    new_user = Users(
        nicedayuid=userid,
        firstname=profile['firstName'],
        lastname=profile['lastName'],
        location=profile['location'],
        gender=profile['gender'],
        dob=profile['birthDate']
    )

    session.add(new_user)
    session.commit()

    print(f'Added new user profile (niceday uid {userid}) to db')


def main():
    parser = argparse.ArgumentParser(description="Onboard the user with the given ID")
    parser.add_argument("userid", type=int, help="User ID on Sensehealth server")
    args = parser.parse_args()
    onboard_user(args.userid)


if __name__ == "__main__":
    main()
