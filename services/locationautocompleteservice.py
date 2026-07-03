import json
import logging
import requests

from config.settings import url_autocomplete, headers
from models.sessionmanager import SessionManager


class LocationAutocompleteService:

    @staticmethod
    def get_location_autocomplete(location: str):
        try:
            url = url_autocomplete + location
            response = SessionManager.get_session().get(url, headers=headers)
            data = json.loads(response.text)
        except (TypeError, requests.exceptions.RequestException, json.JSONDecodeError, KeyError, AttributeError) as e:
            logging.error('Error in get_location_autocomplete: %s', type(e).__name__)
            data = []
        return data
