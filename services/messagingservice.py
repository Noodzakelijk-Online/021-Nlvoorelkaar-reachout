import logging
import random
import time
from typing import Optional, List
from utils.csv_util.csv_util import contact_date_to_csv, pre_send_message_check

from config.settings import headers, url_volunteer, minimum_time, maximum_time, url_base
from controllers.logincontroller import LoginController
from controllers.logincontrollerinterface import LoginControllerInterface
from models.sessionmanager import SessionManager
from bs4 import BeautifulSoup


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

    def send_messages(self, notifier, username: str, password: str, message: str, phoneNumber: str,
                      recipients: List[str]) -> None:
        self.notifier = notifier
        self.username = username
        self.password = password
        self.message = message
        self.phoneNumber = phoneNumber
        self.recipients = recipients
        self.loginController.logout()
        current_recipient = 0
        self.notifier.notify_starting_messaging(self.delay_to_start_sending)
        time.sleep(self.delay_to_start_sending)
        for recipient in self.recipients:
            if pre_send_message_check(recipient):
                if self.__send_message(recipient):
                    time.sleep(1)
                    if self.check_if_message_was_sent(recipient):
                        contact_date_to_csv(recipient)
                    else:
                        print(f"Failed to send message to {recipient}")

            else:
                pass

            current_recipient += 1
            self.notifier.notify_progress_message_sending(current_recipient)
            if current_recipient != len(self.recipients):
                time.sleep(random.uniform(minimum_time, maximum_time))

    def __send_message(self, volunteer_id: str) -> bool:

        url = f'{url_volunteer}{volunteer_id}?showMessage=1'
        try:
            response = SessionManager.get_session().get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                message_token = soup.find('input', {'name': 'message[_token]'})['value']
                message_loaded = soup.find('input', {'name': 'message[loaded]'})['value']
                data = {
                    'message[body]': self.message,
                    'message[phoneNumber]': self.phoneNumber,
                    'message[dusdat]': '',
                    'message[_token]': message_token,
                    'message[loaded]': message_loaded}
            else:
                logging.error(f'Error while sending message to volunteer with id {volunteer_id}: '
                              f'Could not get message page')
                return False
            response = SessionManager.get_session().post(url, data=data, headers=headers)
            if response.status_code != 200:
                time.sleep(1)
                logging.error(f'Error while sending message to volunteer with id {volunteer_id}: '
                                f'Server responded with status code {response.status_code}')
                print(f'Error while sending message to volunteer with id {volunteer_id}: '
                              f'Server responded with status code {response.status_code}')
                return False

            print(f'Message sent to volunteer with id {volunteer_id}' + f' Server responded with status code {response.status_code}')
            return True

        except Exception as e:
            logging.error(f'Error while sending message to volunteer with id {volunteer_id}: {e.__str__()}')
            return False

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
                    logging.error(f'Could not find message sent to volunteer with id {volunteer_id}')
                    self.notifier.notify_message_not_sent(volunteer_id)
                    return False
                else:
                    logging.info(f'Message was sent to volunteer with id {volunteer_id}')
                    print(f'Message to {volunteer_id} was found in messages page')
                    return True
            else:
                logging.error(f'Error while checking if message was sent to volunteer with id {volunteer_id}: '
                              f'Could not get messages page')
                print(f'Error while checking if message was sent to volunteer with id {volunteer_id}: '
                              f'Could not get messages page')
                return False

        except Exception as e:
            logging.error(f'Error while checking if message was sent to volunteer with id {volunteer_id}: {str(e)}')
            return False


