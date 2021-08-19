from niceday_client import NicedayClient


def test_get_profile():
    client = NicedayClient()
    existing_user_id = 38527
    profile = client.get_profile(existing_user_id)
    assert isinstance(profile, dict)
    assert 'id' in profile
    assert 'userProfile' in profile
