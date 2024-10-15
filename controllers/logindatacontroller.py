import json
import os
from typing import Optional
import getpass
import hashlib
import base64
from cryptography.fernet import Fernet

from controllers.logindatacontrollerinterface import LoginDataControllerInterface


class LoginDataController(LoginDataControllerInterface):
    LOGIN_DATA_FILE = ".login_data"
    KEY = base64.urlsafe_b64encode(hashlib.sha256(getpass.getuser().encode()).digest())

    def __init__(self):
        self.cipher_suite = Fernet(LoginDataController.KEY)

    def save_login_data(self, username: str, password: str) -> None:
        encrypted_data = self.cipher_suite.encrypt(json.dumps({"username": username, "password": password}).encode())
        with open(LoginDataController.LOGIN_DATA_FILE, "wb") as file:
            file.write(encrypted_data)

    def load_login_data(self) -> (Optional[str], Optional[str]):
        if os.path.exists(LoginDataController.LOGIN_DATA_FILE):
            with open(LoginDataController.LOGIN_DATA_FILE, "rb") as file:
                encrypted_data = file.read()
            if encrypted_data:
                decrypted_data = json.loads(self.cipher_suite.decrypt(encrypted_data).decode())
                return decrypted_data["username"], decrypted_data["password"]
            return None, None

        else:
            return None, None

    def erase_login_data(self) -> None:
        if os.path.exists(LoginDataController.LOGIN_DATA_FILE):
            os.remove(LoginDataController.LOGIN_DATA_FILE)
