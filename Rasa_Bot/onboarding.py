import argparse

import sys
sys.path.insert(0, "../niceday_client/")

from niceday_client import NicedayClient

def onboard_user(userid):
    client = NicedayClient()
    profile = client.get_profile(userid)
    print(profile)


def main(args=None):

    parser = argparse.ArgumentParser(description="Onboard the user with the given ID")
    parser.add_argument("userid", type=int, help="User ID on Sensehealth server")
    args = parser.parse_args()
    onboard_user(args.userid)

if __name__ == "__main__":
    main()
