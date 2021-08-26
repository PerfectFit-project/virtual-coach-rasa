from unittest import mock

import pytest

from niceday_client import NicedayClient

MOCK_PROFILE_RESPONSE = {'id': 12345, 'networks': [{'networkMemberId': 123456, 'networkId': 112233, 'role': 'patient', 'createdAt': '2021-04-28T10:53:44.438Z', 'isActive': True, 'deletedAt': None, 'deletedBy': None}], 'userProfile': {'firstName': 'Test', 'lastName': 'McTesterson', 'bio': '', 'location': 'Pyteststad', 'birthDate': '1894-01-22', 'gender': 'MALE', 'image': None, 'preferredLanguage': 'en', 'settings': {'app': {'version': 1, 'settings': {'notifications': {'timesPrimed': 2, 'lastPrimingDate': '2222-03-22T11:53:50.106Z'}, 'trackerOrder': [-1, -2, -3, -4, -5, 1], 'appOnboarding': {'welcome': '2021-04-19T12:49:32.800Z', 'finished': 'current_block', 'eventPlanning': '2021-04-19T12:52:05.063Z', 'connectionPath': '2021-04-19T12:50:07.186Z', 'firstRegistration': '2020-05-18T13:52:00.102Z', 'firstRegistrationCompleted': '2020-05-18T15:21:11.762Z'}, 'onboardingUsp': None, 'appOpenedCount': 10, 'dailyTipConfig': {'tipHistory': {'2021-04-19': 'tips.tip33', '2021-04-28': 'tips.tip67', '2021-05-03': 'tips.tipContentExperiment1', '2021-05-04': 'tips.tip40', '2021-05-06': 'tips.tip24', '2021-05-10': 'tips.tip61', '2021-05-11': 'tips.tip63', '2021-05-12': 'tips.tip12', '2021-08-03': 'tips.tip42'}}, 'networkOnboarding': None, 'trackingOnboarding': None, 'stepCountOnboarding': None, 'dailyPlannerOnboarding': None, 'onboardingChallengeEvents': [], 'feedbackCTAReminderDate': None, 'feedbackSentOrSkippedDate': None, 'dontShowRecurringEventInfo': False, 'dontShowThoughtRecordsIntro': False, 'firstOnboardingExperimentOption': None, 'lastRegistrationValueByTrackerName': {}}}}}, 'user': {'username': 'test.test@test.nl', 'email': 'test.test@test.nl', 'isActive': True, 'dateJoined': '2020-05-13T18:49:12.025Z', 'isPublic': True, 'hashId': 'testtesttest', 'id': 12345}} # noqa


@pytest.mark.integration
def test_get_profile_from_server():
    """
    Test fetching of a (known) user from the Sensehealth server
    """
    client = NicedayClient()
    existing_user_id = 38527
    profile = client.get_profile(existing_user_id)
    assert isinstance(profile, dict)
    assert 'id' in profile
    assert 'userProfile' in profile


@mock.patch('niceday_client.NicedayClient._niceday_api')
def test_get_profile(mock_niceday_api):
    """
    Unit test for NanopubClient.get_profile() method with mocked server
    """
    mock_niceday_api.return_value = MOCK_PROFILE_RESPONSE
    client = NicedayClient()
    profile = client.get_profile(12345)
    assert isinstance(profile, dict)

    assert 'id' not in profile
    assert 'userProfile' not in profile

    keys = ['firstName', 'lastName', 'location',
            'birthDate', 'gender']
    for k in keys:
        assert k in profile
        assert isinstance(profile[k], str)
