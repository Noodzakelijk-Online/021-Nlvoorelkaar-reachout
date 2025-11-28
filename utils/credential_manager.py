"""
Secure Credential Manager for NLvoorelkaar Tool
Handles encryption and decryption of user credentials locally
"""

import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class CredentialManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.credentials_file = os.path.join(data_dir, "credentials.enc")
        self.salt_file = os.path.join(data_dir, "salt.key")
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
            os.chmod(self.salt_file, 0o600)  # Secure permissions
            return salt
            
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
            os.chmod(self.credentials_file, 0o600)  # Secure permissions
            
            logger.info("Credentials saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
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
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
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
            
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
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
            
        except Exception as e:
            logger.error(f"Failed to change master password: {e}")
            return False

