from abc import ABC, abstractmethod


class LoginControllerInterface(ABC):

    @abstractmethod
    def login(self, username, password):
        pass

    @abstractmethod
    def logout(self):
        pass
