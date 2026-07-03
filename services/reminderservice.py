try:
    from google_drive.google_api_services import GoogleDriveManager
except ModuleNotFoundError:
    GoogleDriveManager = None
from datetime import datetime
from typing import Optional
import logging
import requests

from config.settings import headers
from controllers.logincontroller import LoginController
from controllers.logincontrollerinterface import LoginControllerInterface
from models.sessionmanager import SessionManager
from bs4 import BeautifulSoup, PageElement

from models.stringlist import StringLists
try:
    from services.blacklistservice import BlacklistService
except ModuleNotFoundError:
    BlacklistService = None


REMINDER_APPROVAL_ERROR = (
    "Legacy reminder sending is disabled. Use OutreachLedger follow-up plans, "
    "approval, and send evidence so every reminder is reviewed and auditable."
)


class ReminderService:
    def __init__(self, loginController: Optional[LoginControllerInterface] = None):
        self.blService = BlacklistService() if BlacklistService else None
        self.message = None
        self.username = None
        self.password = None
        self.notifier = None
        self.stopped = False
        self.loginController = loginController if loginController else LoginController()
        self.google_drive_manager = GoogleDriveManager() if GoogleDriveManager else None

    def run_reminder_service(self, reminder_frequency: Optional[str] = None,
                             reminder_message: Optional[str] = None):
        """Refuse the legacy reminder workflow; follow-ups must use the ledger."""
        raise RuntimeError(REMINDER_APPROVAL_ERROR)


    def get_all_contacted_names(self) -> StringLists | bool:

        """
        Get all contacted names

        return: StringLists object with names and urls
        """
        print("Collecting all chats...")
        urls = []
        url = 'https://www.nlvoorelkaar.nl/mijn-pagina/berichten'
        urls.append(url)
        response = SessionManager.get_session().get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paginator = soup.find('div', {'class': 'paginator'})

            if paginator:
                pages = paginator.find_all('a')
                for page in pages:
                    if not page.text.isalpha():
                        page_number = int(page.text)
                        if page_number > 1:
                            url = f'https://www.nlvoorelkaar.nl/mijn-pagina/berichten?p={page_number}'
                            urls.append(url)
            volunteers_names = []
            for url in urls:
                response = SessionManager.get_session().get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                volunteers = soup.find_all('a', {'aria-labelledby': 'message-of-label'})
                for volunteer_name in volunteers:
                    volunteers_names.append(volunteer_name.text)

            result = StringLists(volunteers_names, urls)
            return result



    @staticmethod
    def check_with_frequency(str_date, frequency):
        """
            Check if the last reminder to this chat was sent more than 3 days ago

            param: str_date: string date in format 'YYYY-MM-DD'

            return: bool: True if the last reminder was sent more than specified frequency ago, False otherwise
        """

        today = datetime.now()
        last_check = datetime.strptime(str_date, '%Y-%m-%d')
        delta = today - last_check
        return delta.days >= int(frequency)

    def construct_message(self, chat_url: str):
        """
            Construct the message to be sent to the receiver

            param: chat_url: string url of the chat

            return: string: message to be sent
        """

        sender_name = self.get_sender_name()
        receiver_name = self.get_receiver_name(chat_url)
        message = self.format_message(sender_name, receiver_name)
        return message

    @staticmethod
    def format_message(sender_name: str, receiver_name: str):
        """
            Format the message to be sent to the receiver placing the names in the message

            param: sender_name: string name of the sender
            param: receiver_name: string name of the receiver

            return: string: formatted message
        """
        message = f'''
    Hello {receiver_name},
    
    Were you able to check my request and if so, could you tell me if you are interested?
    I am looking forward to your response,
    
    Yours Sincerely,
    {sender_name}
        '''
        return message

    def send_reminder(self, chat_url: str, message: Optional[str] = None):
        """
                Refuse legacy direct reminder sending.

                param: chat_url: string url of the chat
                param: message: string message to be sent

                raises: RuntimeError because follow-ups require ledger approval
            """
        raise RuntimeError(REMINDER_APPROVAL_ERROR)


    def csv_handler(self, chats_with_no_response, reminder_frequency: int, reminder_message: Optional[str] = None):
        """Refuse legacy CSV-driven reminder sending."""
        raise RuntimeError(REMINDER_APPROVAL_ERROR)

    def construct_message(self, chat_url: str) -> str:
        """
        Construct the message to be sent to the receiver

        :param chat_url: string url of the chat
        :return: string: message to be sent
        """
        sender_name = self.get_sender_name()
        receiver_name = self.get_receiver_name(chat_url)
        message = self.format_message(sender_name, receiver_name)
        return message

    def get_unanswered_chats(self, reminder_frequency: int):

        """
            Check each chat for a response

            return: list of chat_urls with no response
            """
        names_urls_object = self.get_all_contacted_names()
        chats_with_no_response = set()

        try:
            volunteer_names = names_urls_object.names

            urls = names_urls_object.pages


            for url in urls:
                response = SessionManager.get_session().get(url, headers=headers)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    chats = soup.find_all('li', {'class': 'list__item list__item--messages'})

                    for chat in chats:
                        chat_url = chat.find('a', {'class': 'button button--primary button--detail'})
                        if chat_url:
                            chat_url = "https://www.nlvoorelkaar.nl" + chat_url['href']

                            response = SessionManager.get_session().get(chat_url, headers=headers)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            message_metas = soup.find_all('p', {'class': 'meta conversation__meta'})

                            if self.check_last_message_date(message_metas, int(reminder_frequency)):
                                message_authors = []
                                for message_meta in message_metas:
                                    author = message_meta.text.split(' ')[0]
                                    if author in volunteer_names and not self.check_60_days(message_meta):
                                        message_authors.append(author)

                                if len(message_authors) == 0:
                                    chats_with_no_response.add(chat_url)

                                    continue

                            else:
                                pass



                else:
                    logging.error(f'Error while checking unanswered messages: Could not get messages page')
                    return False
        except (AttributeError, TypeError, IndexError, KeyError, requests.exceptions.RequestException, ValueError) as e:
            logging.error('Error while checking unanswered messages: %s', type(e).__name__)
            return False
        return chats_with_no_response

    def get_sender_name(self):
        """
                Get the name of the sender of the chat

                return: string: name of the sender
            """
        try:
            url = 'https://www.nlvoorelkaar.nl/en/mijn-pagina/profiel'
            response = SessionManager.get_session().get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                name = soup.find('input', {'id': 'user_profile_firstName'})['value']
                return name
        except (AttributeError, TypeError, KeyError, requests.exceptions.RequestException, ValueError) as e:
            logging.error('Error while getting sender name: %s', type(e).__name__)
            return False

    def get_receiver_name(self, chat_url: str):
        """
            Get the name of the receiver of the chat

            param: chat_url: string url of the chat

            return: string: name of the receiver

        """

        if chat_url:
            try:

                response = SessionManager.get_session().get(chat_url, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # find by xpath
                    receiver_name = soup.find('dl', {
                        'class': 'list__definition list__definition--horizontal list__definition--plain list-definition--small'}).text.split(
                        '\n')[2].strip()
                    return receiver_name
            except (AttributeError, TypeError, IndexError, ValueError) as e:
                logging.error('Error while getting receiver name: %s', type(e).__name__)
                return False

    def check_last_message_date(self, message_metas, reminder_frequency: int):
        """
            Check if the last message on the page was sent more than {reminder_frequency} days ago

            param: chat_url: string url of the chat
            param: reminder_frequency: int frequency of the reminders

            return: bool: True if the last message was sent more than 3 days ago, False otherwise
        """

        try:

            last_message_date = message_metas[-1].text[-16:-6:1]

            today = datetime.now()
            last_message_date = datetime.strptime(last_message_date, '%d.%m.%Y')

            delta = today - last_message_date

            return delta.days >= reminder_frequency
        except (AttributeError, TypeError, IndexError, ValueError) as e:
            logging.error('Error while checking last message date: %s', type(e).__name__)
            return False

    def check_60_days(self, message_meta: PageElement):
        """
            Check if the last message on the page was sent more than 60 days ago

            param: message_meta: string meta of the message

            return: bool: True if the last message was sent more than 60 days ago, False otherwise
        """
        try:
            last_message_date = message_meta.text[-16:-6:1]

            today = datetime.now()
            last_message_date = datetime.strptime(last_message_date, '%d.%m.%Y')

            delta = today - last_message_date

            return delta.days >= 60
        except (AttributeError, TypeError, IndexError, ValueError) as e:
            logging.error('Error while checking last message date: %s', type(e).__name__)
            return False

    def stop_reminder_service(self):
        """
        Stop the reminder service
        """
        self.stopped = True
