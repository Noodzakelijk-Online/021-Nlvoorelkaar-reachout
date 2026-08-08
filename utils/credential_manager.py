"""
Secure Credential Manager for NLvoorelkaar Tool
Handles encryption and decryption of user credentials locally
"""

import os
import json
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class CredentialManager:
    def __init__(self, data_dir="data"):
        if os.path.splitext(data_dir)[1]:
            self.data_dir = os.path.dirname(data_dir) or "."
            self.credentials_file = data_dir
        else:
            self.data_dir = data_dir
            self.credentials_file = os.path.join(data_dir, "credentials.enc")
        self.salt_file = os.path.join(self.data_dir, "salt.key")
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, mode=0o700)  # Secure permissions
            
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
        
    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one"""
        if os.path.exists(self.salt_file):
            with open(self.salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            self._chmod_private(self.salt_file)
            return salt

    @staticmethod
    def _chmod_private(path: str) -> None:
        """Apply private file permissions on platforms that support chmod."""
        try:
            os.chmod(path, 0o600)
        except OSError:
            logger.debug("Could not set private permissions on %s", path)
            
    def save_credentials(self, username: str, password: str, master_password: str) -> bool:
        """Save encrypted credentials"""
        try:
            salt = self._get_or_create_salt()
            key = self._derive_key(master_password, salt)
            fernet = Fernet(key)
            
            credentials = {
                "username": username,
                "password": password,
                "timestamp": str(int(os.path.getmtime(__file__) if os.path.exists(__file__) else 0))
            }
            
            encrypted_data = fernet.encrypt(json.dumps(credentials).encode())
            
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            self._chmod_private(self.credentials_file)
            
            logger.info("Credentials saved successfully")
            return True
            
        except (OSError, ValueError, TypeError) as e:
            logger.error("Failed to save credentials: %s", type(e).__name__)
            return False
            
    def load_credentials(self, master_password: str) -> dict:
        """Load and decrypt credentials"""
        try:
            if not os.path.exists(self.credentials_file):
                return None
                
            salt = self._get_or_create_salt()
            key = self._derive_key(master_password, salt)
            fernet = Fernet(key)
            
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
                
            decrypted_data = fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            logger.info("Credentials loaded successfully")
            return credentials
            
        except (OSError, json.JSONDecodeError, TypeError, ValueError, InvalidToken) as e:
            logger.error("Failed to load credentials: %s", type(e).__name__)
            return None
            
    def credentials_exist(self) -> bool:
        """Check if encrypted credentials exist"""
        return os.path.exists(self.credentials_file)
        
    def delete_credentials(self) -> bool:
        """Securely delete credentials"""
        try:
            if os.path.exists(self.credentials_file):
                # Overwrite file with random data before deletion
                file_size = os.path.getsize(self.credentials_file)
                with open(self.credentials_file, 'wb') as f:
                    f.write(os.urandom(file_size))
                os.remove(self.credentials_file)
                
            if os.path.exists(self.salt_file):
                os.remove(self.salt_file)
                
            logger.info("Credentials deleted successfully")
            return True
            
        except OSError as e:
            logger.error("Failed to delete credentials: %s", type(e).__name__)
            return False
            
    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """Change master password"""
        try:
            # Load credentials with old password
            credentials = self.load_credentials(old_password)
            if not credentials:
                return False
                
            # Delete old files
            self.delete_credentials()
            
            # Save with new password
            return self.save_credentials(
                credentials["username"], 
                credentials["password"], 
                new_password
            )
            
        except (TypeError, KeyError, OSError, ValueError) as e:
            logger.error("Failed to change master password: %s", type(e).__name__)
            return False

    def has_credentials(self, service: str = "default") -> bool:
        """Compatibility helper for enhanced entry points."""
        return self.credentials_exist()

    def store_credentials(self, service: str, credentials: dict, master_password: str = None) -> bool:
        """
        Store a service credential bundle.

        Existing UI flows use save_credentials(username, password, master_password).
        Compatibility callers must also provide an explicit master password, either
        as an argument or through NLVE_MASTER_PASSWORD.
        """
        master = master_password or os.environ.get("NLVE_MASTER_PASSWORD")
        if not master:
            logger.error("Refusing credential storage without an explicit master password")
            return False
        username = credentials.get("username") or credentials.get("email") or credentials.get("user", "")
        password = credentials.get("password", "")
        payload = {
            "username": username,
            "password": password,
            "service": service,
            "extra": {k: v for k, v in credentials.items() if k not in {"username", "email", "user", "password"}}
        }

        try:
            salt = self._get_or_create_salt()
            fernet = Fernet(self._derive_key(master, salt))
            with open(self.credentials_file, "wb") as f:
                f.write(fernet.encrypt(json.dumps(payload).encode()))
            self._chmod_private(self.credentials_file)
            return True
        except (OSError, TypeError, ValueError, KeyError) as e:
            logger.error("Failed to store credentials: %s", type(e).__name__)
            return False

    def get_credentials(self, service: str = "default", master_password: str = None) -> dict:
        """Compatibility helper for enhanced services."""
        master = master_password or os.environ.get("NLVE_MASTER_PASSWORD")
        if not master:
            logger.error("Refusing credential load without an explicit master password")
            return {}
        credentials = self.load_credentials(master)
        if not credentials:
            return {}
        if credentials.get("service") and credentials.get("service") != service:
            return {}
        result = credentials.get("extra", {}).copy()
        result["username"] = credentials.get("username")
        result["password"] = credentials.get("password")
        return result
