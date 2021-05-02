import requests
from pandas_ods_reader import read_ods
import logging

from config import MANAGED_CONTENT_URL, MANAGED_CONTENT_TEMP_ODS_LOCATION

class ManagedContentReader:

    """
    ManagedContentReader will fetch the content at the location indicated by MANAGED_CONTENT_URL,
    storing it as a pandas dataframe. Provides methods for reading this content. At present
    the data at MANAGED_CONTENT_URL must be in ODS format.
    """
    def __init__(self):
        r = requests.get(MANAGED_CONTENT_URL)
        if r.status_code != 200:
            logging.error(f'Failed to fetch from URL: {MANAGED_CONTENT_URL} - received response {r.status_code}.')
            raise Exception('Could not initialise ManagedContentReader - Failed to fetch from CMS URL')

        # Write response body to local file
        with open(MANAGED_CONTENT_TEMP_ODS_LOCATION, 'wb') as outfile:
            outfile.write(r.content)

        # Attempt to read ODS into pandas dataframe
        try:
            self.content_df = read_ods(MANAGED_CONTENT_TEMP_ODS_LOCATION, sheet=1)
        except KeyError as ke:
            logging.error(f'Response from {MANAGED_CONTENT_URL} does not look like an ODS file: KeyError {ke}.')
            raise Exception('Could not initialise ManagedContentReader - Response was not an ODS file.')

    def get_random_content(self):
        """
        Returns one record, at random, from the spreadsheet obtained from MANAGED_CONTENT_URL.
        This record is returned as a Dict with all columns of the original spreadsheet as keys.
        """
        random_row = self.content_df.sample().to_dict("records")[0]
        return random_row


if __name__ == "__main__":
    content = ManagedContentReader()
    print('Fetching random row from psycho education csv:', content.get_random_content())
    print('Fetching another random row from psycho education csv:', content.get_random_content())

