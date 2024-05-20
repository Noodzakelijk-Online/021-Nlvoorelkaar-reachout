import requests


class SessionManager:
    _session = None

    @staticmethod
    def get_session():
        if SessionManager._session is None:
            SessionManager._session = requests.Session()
        return SessionManager._session
