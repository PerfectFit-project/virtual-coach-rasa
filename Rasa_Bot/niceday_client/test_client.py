from niceday_client import NicedayClient

client = NicedayClient()

profile = client.get_profile(38527)
print(profile)
