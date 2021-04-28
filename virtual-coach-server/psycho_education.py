import requests
import csv
from io import StringIO
import random
import logging

from config import PSYCHO_EDUCATION_URL


def fetch_random_psycho_education():
    r = requests.get(PSYCHO_EDUCATION_URL)
    if r.status_code != 200:
        logging.error(f'Failed to fetch CSV from URL: {PSYCHO_EDUCATION_URL} - received response {r.status_code}.')
        return None

    # Read CSV from response body and return random row
    reader = csv.DictReader(StringIO(r.text))
    csvrows = list(reader)
    if 'Formulation Email' not in csvrows[0]:
        logging.error(f'Response from URL {PSYCHO_EDUCATION_URL} was not valid csv. No "Formulation Email" column.')
        return None
    return random.choice(csvrows)


if __name__ == "__main__":
    print('Fetching random row from psycho education csv:', fetch_random_psycho_education())
