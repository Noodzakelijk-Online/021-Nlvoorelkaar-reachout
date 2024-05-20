import json
import logging

from config.settings import url_autocomplete, headers
from models.sessionmanager import SessionManager


class LocationAutocompleteService:

    @staticmethod
    def get_location_autocomplete(location: str):
        try:
            url = url_autocomplete + location
            response = SessionManager.get_session().get(url, headers=headers)
            data = json.loads(response.text)
        except Exception as e:
            logging.error(f'Error in get_location_autocomplete: {e}')
            data = []
        return data
