import csv
import time
from datetime import datetime
from random import random, randint
from typing import Optional
import logging

from config.settings import headers
from controllers.logincontroller import LoginController
from controllers.logincontrollerinterface import LoginControllerInterface
from models.sessionmanager import SessionManager
from bs4 import BeautifulSoup

from models.stringlist import StringLists


class ReminderService:
    def __init__(self, loginController: Optional[LoginControllerInterface] = None):
        self.message = None
        self.username = None
        self.password = None
        self.notifier = None
        self.loginController = loginController if loginController else LoginController()

    def start_reminder_service(self, notifier, reminder_frequency):

        """
            Start the reminder service
        """

        chats_with_no_response = self.get_unanswered_chats(reminder_frequency)

        if chats_with_no_response:
            notifier.notify_unanswered_chats(chats_with_no_response)
            self.csv_handler(chats_with_no_response, reminder_frequency)

        else:
            notifier.notify_unanswered_chats(["No unanswered chats found"])


    def get_all_contacted_names(self) -> StringLists | bool:

        """
        Get all contacted names

        return: StringLists object with names and urls
        """
        try:
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
                volunteers_ids = []
                for url in urls:
                    response = SessionManager.get_session().get(url, headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    volunteers = soup.find_all('a', {'aria-labelledby': 'message-of-label'})
                    for volunteer_name in volunteers:
                        volunteers_names.append(volunteer_name.text)

                result = StringLists(volunteers_names, urls)
                return result

        except Exception as e:
            logging.error(f'Error while collecting contacted names: {str(e)}')
            return False

    @staticmethod
    def check_with_frequency(str_date, frequency):
        """
            Check if the last reminder to this chat was sent more than 3 days ago

            param: str_date: string date in format 'YYYY-MM-DD'

            return: bool: True if the last reminder was sent more than specified frequency ago or more, False otherwise
        """

        today = datetime.now()
        last_check = datetime.strptime(str_date, '%Y-%m-%d')
        delta = today - last_check
        return delta.days >= frequency

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

    def send_reminder(self, chat_url: str):
        """
                Send a reminder to the receiver of the chat

                param: chat_url: string url of the chat
                param: message: string message to be sent

                return: bool: True if the message was sent successfully, False otherwise
            """

        if chat_url:
            try:
                response = SessionManager.get_session().get(chat_url, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    message_token = soup.find('input', {'name': 'message[_token]'})['value']
                    message_loaded = soup.find('input', {'name': 'message[loaded]'})['value']
                    sender_name = self.get_sender_name()
                    receiver_name = self.get_receiver_name(chat_url)

                    message = self.format_message(sender_name, receiver_name)
                    data = {
                        'message[body]': message,
                        'message[dusdat]': '',
                        'message[_token]': message_token,
                        'message[loaded]': message_loaded
                    }

                    # sleep between 30 and 75 seconds
                    time.sleep(randint(30, 75))
                    response = SessionManager.get_session().post(chat_url, data=data, headers=headers)
                    if response.status_code == 200:
                        return True
            except Exception as e:
                logging.error(f'Error while sending reminder to chat with url {chat_url}: {str(e)}')
                return False

    def csv_handler(self, chats_with_no_response, reminder_frequency):
        if not chats_with_no_response:
            return


        with open('chats_no_response.csv', 'r+', newline='') as file:
            reader = csv.reader(file)
            writer = csv.writer(file)

            rows_in_file = list(reader)
            updated_rows = []

            for chat_url in chats_with_no_response:
                chat_exists = False
                for i, row in enumerate(rows_in_file):
                    if len(row) > 0 and row[0] == chat_url:
                        chat_exists = True
                        if self.check_with_frequency(row[1], reminder_frequency) and int(row[2]) <= 4:
                            rows_in_file[i] = [chat_url, datetime.now().strftime('%Y-%m-%d'), str(int(row[2]) + 1)]
                            self.send_reminder(chat_url)
                            print(f"Reminder sent to {chat_url}")
                        elif self.check_with_frequency(row[1], reminder_frequency) and int(row[2]) > 4:
                            print(f"Chat {chat_url} has been banned to send more reminders")
                        elif not self.check_with_frequency(row[1], reminder_frequency):
                            print(f"Message is not older than {reminder_frequency} days for {chat_url}")

                if not chat_exists:
                    new_row = [chat_url, datetime.now().strftime('%Y-%m-%d'), '0']
                    updated_rows.append(new_row)
                    self.send_reminder(chat_url)
                    print(f"Sent message to {chat_url}")

            # Remove old rows from updated rows
            updated_rows = [row for row in updated_rows if row not in rows_in_file]

            # Combine updated rows with existing rows
            updated_rows.extend(rows_in_file)

            file.seek(0)
            writer.writerows(updated_rows)
            file.truncate()

    def get_unanswered_chats(self, reminder_frequency: int):

        """
            Check each chat for a response

            return: list of chat_urls with no response
            """

        names_urls_object = self.get_all_contacted_names()
        chats_with_no_response = []

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
                        if chat_url:  # Check if chat_url exists before accessing href
                            chat_url = "https://www.nlvoorelkaar.nl" + chat_url['href']

                            response = SessionManager.get_session().get(chat_url, headers=headers)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            message_metas = soup.find_all('p', {'class': 'meta conversation__meta'})

                            if self.check_last_message_date(message_metas, reminder_frequency):
                                message_authors = []
                                for message_meta in message_metas:
                                    author = message_meta.text.split(' ')[0]
                                    if author in volunteer_names:
                                        message_authors.append(author)
                                if len(message_authors) == 0:
                                    chats_with_no_response.append(chat_url)

                                    continue

                            else:
                                pass



                else:
                    logging.error(f'Error while checking unanswered messages: Could not get messages page')
                    return False
        except Exception as e:
            logging.error(f'Error while checking unanswered messages: {str(e)}')
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
        except Exception as e:
            logging.error(f'Error while getting sender name: {str(e)}')
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
            except Exception as e:
                logging.error(f'Error while getting receiver name: {str(e)}')
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
        except Exception as e:
            print(f'Error while checking last message date: {str(e)}')
            return False
