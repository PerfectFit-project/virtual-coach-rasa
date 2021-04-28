import requests
from io import StringIO
from pandas_ods_reader import read_ods
import logging

from config import PSYCHO_EDUCATION_URL, TEMP_PSYCHO_EDUCATION_ODS_LOCATION


def fetch_random_psycho_education():
    r = requests.get(PSYCHO_EDUCATION_URL)
    if r.status_code != 200:
        logging.error(f'Failed to fetch CSV from URL: {PSYCHO_EDUCATION_URL} - received response {r.status_code}.')
        return None

    # Convert response body to pandas dataframe
    with open(TEMP_PSYCHO_EDUCATION_ODS_LOCATION, 'wb') as outfile:
        outfile.write(r.content)
    df = read_ods(TEMP_PSYCHO_EDUCATION_ODS_LOCATION, sheet=1)

    # Choose a row at random, and return it as a dict
    random_row = df.sample().to_dict("records")[0]
    return random_row


if __name__ == "__main__":
    print('Fetching random row from psycho education csv:', fetch_random_psycho_education())
