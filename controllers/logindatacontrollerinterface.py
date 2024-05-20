from abc import ABC, abstractmethod
from typing import Optional, Tuple


class LoginDataControllerInterface(ABC):
    @abstractmethod
    def save_login_data(self, username: str, password: str) -> None: pass

    @abstractmethod
    def load_login_data(self) -> Optional[Tuple[str, str]]: pass

    @abstractmethod
    def erase_login_data(self) -> None: pass
