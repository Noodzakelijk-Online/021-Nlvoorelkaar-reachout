import time

from config.settings import url_login_page, headers, url_login, url_logout
from controllers.logincontrollerinterface import LoginControllerInterface
from models.sessionmanager import SessionManager
from bs4 import BeautifulSoup


class LoginController(LoginControllerInterface):

    def login(self, username: str, password: str) -> bool:
        response = SessionManager.get_session().get(url_login_page, headers=headers)
        time.sleep(2)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': '_csrf_token'})['value']
        data = {
            '_csrf_token': csrf_token,
            '_username': username,
            '_password': password,
            '_remember_me': 'on'
        }

        response = SessionManager.get_session().post(url_login, data=data, headers=headers)
        return response.status_code == 200 and response.url == 'https://www.nlvoorelkaar.nl/mijn-pagina/berichten' \
                                                               '?authentication=success'

    def logout(self) -> bool:
        response = SessionManager.get_session().get(url_logout, headers=headers)
        return response.status_code == 302




