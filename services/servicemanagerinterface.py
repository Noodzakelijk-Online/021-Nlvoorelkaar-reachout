from abc import ABC, abstractmethod
from typing import Any


class ServiceManagerInterface(ABC):

    @abstractmethod
    def subscribe(self, observer: Any) -> None:
        pass

    @abstractmethod
    def notify_location_auto_complete(self, data):
        pass

    @abstractmethod
    def notify_total_volunteers(self, data):
        pass

    @abstractmethod
    def get_location_data(self, location):
        pass

    @abstractmethod
    def get_amount_of_volunteer(self, checkbox_vars, location_ids_types, location, distance):
        pass

    @abstractmethod
    def unsubscribe(self, observer: Any) -> None:
        pass

    def get_volunteers(self, checkbox_vars, location_ids_types, param, param1):
        pass

    def send_messages(self, username, password, param, param1, data):
        pass

    def start_reminder_service(self, reminder_frequency):
        pass

    def get_unanswered_chats(self, reminder_frequency):
        pass
