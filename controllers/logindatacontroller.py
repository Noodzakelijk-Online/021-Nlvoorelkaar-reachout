"""OS-keyring storage for the retired classic login view."""

from typing import Optional, Tuple

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from controllers.logindatacontrollerinterface import LoginDataControllerInterface


class LoginDataController(LoginDataControllerInterface):
    """Store remembered credentials in the operating-system credential vault."""

    SERVICE = "NoodzakelijkOnline.NLvoorelkaarReachout"
    USERNAME_KEY = "username"
    PASSWORD_KEY = "password"

    def save_login_data(self, username: str, password: str) -> None:
        if not username or not password:
            raise ValueError("username and password are required")
        keyring.set_password(self.SERVICE, self.USERNAME_KEY, username)
        keyring.set_password(self.SERVICE, self.PASSWORD_KEY, password)

    def load_login_data(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            return (
                keyring.get_password(self.SERVICE, self.USERNAME_KEY),
                keyring.get_password(self.SERVICE, self.PASSWORD_KEY),
            )
        except KeyringError:
            return None, None

    def erase_login_data(self) -> None:
        for key in (self.USERNAME_KEY, self.PASSWORD_KEY):
            try:
                keyring.delete_password(self.SERVICE, key)
            except (PasswordDeleteError, KeyringError):
                pass
