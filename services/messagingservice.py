import logging
import random
import time
from typing import Optional, List
import requests

try:
    from google_drive.google_api_services import GoogleDriveManager
except ModuleNotFoundError:
    GoogleDriveManager = None
try:
    from services.blacklistservice import BlacklistService
except ModuleNotFoundError:
    BlacklistService = None
try:
    from utils.csv_util.csv_util import contact_date_to_csv, pre_send_message_check
except ModuleNotFoundError:
    contact_date_to_csv = None
    pre_send_message_check = None

from config.settings import headers, url_volunteer, minimum_time, maximum_time, url_base
from controllers.logincontroller import LoginController
from controllers.logincontrollerinterface import LoginControllerInterface
from models.sessionmanager import SessionManager
from bs4 import BeautifulSoup

from utils.profile_id_extractor import get_profile_id


class MessagingService:

    def __init__(self, loginController: Optional[LoginControllerInterface] = None):

        self.recipients = None
        self.phoneNumber = None
        self.message = None
        self.password = None
        self.username = None
        self.notifier = None
        self.delay_to_start_sending = random.uniform(10.141516, 29.141516)
        self.loginController = loginController if loginController else LoginController()
        self.google_drive_manager = GoogleDriveManager() if GoogleDriveManager else None
        self.blService = BlacklistService() if BlacklistService else None

    def send_messages(self, notifier, username: str, password: str, message: str, phoneNumber: str,
                      recipients: List[str]) -> None:
        raise RuntimeError(
            "Legacy direct sending is disabled. Use OutreachLedger.send_approved_drafts "
            "so every message has a reviewed draft, approval, send attempt, evidence, and audit trail."
        )

    def __send_message(self, volunteer_id: str) -> bool:
        raise RuntimeError(
            "Legacy direct sending is disabled. Use OutreachLedger.send_approved_drafts "
            "so every message has a reviewed draft, approval, send attempt, evidence, and audit trail."
        )

    def check_if_message_was_sent(self, volunteer_id: str):
        """
        Check if the message was sent to the volunteer.

        :param volunteer_id: The id of the volunteer.

        :return: True if the message was sent, False otherwise.
        """

        url = "https://www.nlvoorelkaar.nl/mijn-pagina/berichten"
        try:
            response = SessionManager.get_session().get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                volunteer_names = soup.find_all('a', {'aria-labelledby': 'ad-label'})[:1]
                # extract href from volunteer names
                volunteer_ids = [volunteer_name['href'].split('/')[-1] for volunteer_name in volunteer_names]
                result = False
                for volunteer in volunteer_ids:
                    if volunteer == volunteer_id:
                        result = True
                        break
                if not result:
                    logging.error('Could not find expected sent message for volunteer')
                    self.notifier.notify_message_not_sent(volunteer_id)
                    return False
                else:
                    logging.info('Message was found in messages page')
                    return True
            else:
                logging.error('Error while checking sent message status: could not get messages page')
                return False

        except (AttributeError, KeyError, TypeError, requests.exceptions.RequestException, IndexError) as e:
            logging.error('Error while checking sent message status: %s', type(e).__name__)
            return False


