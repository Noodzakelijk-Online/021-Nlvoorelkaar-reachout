"""
Secure Credential Manager with Rotation and Validation
Addresses TODO items #2: Credential Security - rotation and validation
"""

import os
import json
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import re

try:
    import keyring
except ImportError:
    keyring = None

logger = logging.getLogger(__name__)

# Constants
KEYRING_SERVICE = "nlvoorelkaar"
CREDENTIAL_VERSION = 2
MAX_PASSWORD_AGE_DAYS = 90


@dataclass
class CredentialMetadata:
    """Metadata for stored credentials"""
    version: int = CREDENTIAL_VERSION
    created_at: str = ""
    last_rotated: str = ""
    rotation_count: int = 0
    last_validated: str = ""
    validation_status: str = "unknown"
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialMetadata':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CredentialValidator:
    """Validates credentials before storage"""
    
    # Email validation pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, str]:
        """
        Validate email format
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "E-mailadres is verplicht"
        
        email = email.strip().lower()
        
        if not cls.EMAIL_PATTERN.match(email):
            return False, "Ongeldig e-mailadres formaat"
        
        if len(email) > 254:
            return False, "E-mailadres is te lang"
        
        return True, ""
    
    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Wachtwoord is verplicht"
        
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"Wachtwoord moet minimaal {cls.MIN_PASSWORD_LENGTH} tekens bevatten"
        
        # Check for common weak patterns
        weak_patterns = ['password', 'wachtwoord', '12345678', 'qwerty', 'admin']
        if password.lower() in weak_patterns:
            return False, "Wachtwoord is te zwak"
        
        return True, ""
    
    @classmethod
    def validate_credentials(cls, email: str, password: str) -> Tuple[bool, str]:
        """
        Validate both email and password
        
        Args:
            email: Email address
            password: Password
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        email_valid, email_error = cls.validate_email(email)
        if not email_valid:
            return False, email_error
        
        password_valid, password_error = cls.validate_password(password)
        if not password_valid:
            return False, password_error
        
        return True, ""


class SecureCredentialManager:
    """
    Secure credential management with encryption, rotation, and validation
    
    Features:
    - AES-256 encryption for stored credentials
    - Credential validation before storage
    - Automatic rotation reminders
    - Secure key derivation from master password
    - Keyring integration for system-level security
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize the credential manager
        
        Args:
            master_password: Optional master password for encryption
        """
        self._master_password = None
        self._fernet: Optional[Fernet] = None
        if master_password and os.path.splitext(str(master_password))[1]:
            self._credentials_file = str(master_password)
        else:
            self._master_password = master_password
            self._credentials_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                '.credentials.enc'
            )
        self._metadata_file = os.path.join(
            os.path.dirname(self._credentials_file) or os.path.dirname(os.path.dirname(__file__)),
            '.credentials.meta'
        )
        
        if self._master_password:
            self._init_encryption(self._master_password)
    
    def _init_encryption(self, master_password: str) -> None:
        """Initialize encryption with master password"""
        # Generate salt (or load existing)
        salt_file = os.path.join(os.path.dirname(self._credentials_file), '.salt')
        
        if os.path.exists(salt_file):
            with open(salt_file, 'rb') as f:
                salt = f.read()
        else:
            salt = secrets.token_bytes(16)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            os.chmod(salt_file, 0o600)
        
        # Derive key from master password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self._fernet = Fernet(key)
    
    def set_master_password(self, master_password: str) -> None:
        """Set or change the master password"""
        self._master_password = master_password
        self._init_encryption(master_password)
    
    def store_credentials(
        self,
        email: str,
        password: str,
        validate: bool = True
    ) -> Tuple[bool, str]:
        """
        Store credentials securely
        
        Args:
            email: Email address
            password: Password
            validate: Whether to validate credentials before storing
            
        Returns:
            Tuple of (success, message)
        """
        # Validate if requested
        if validate:
            is_valid, error = CredentialValidator.validate_credentials(email, password)
            if not is_valid:
                return False, error
        
        try:
            # Prepare credential data
            credentials = {
                'email': email.strip().lower(),
                'password': password
            }
            
            # Encrypt and store
            if self._fernet:
                encrypted = self._fernet.encrypt(json.dumps(credentials).encode())
                with open(self._credentials_file, 'wb') as f:
                    f.write(encrypted)
                os.chmod(self._credentials_file, 0o600)
            else:
                # Use system keyring as fallback
                if keyring is None:
                    return False, "Keyring is not installed and no master password was provided"
                keyring.set_password(KEYRING_SERVICE, 'email', email)
                keyring.set_password(KEYRING_SERVICE, 'password', password)
            
            # Update metadata
            now = datetime.now().isoformat()
            metadata = self._load_metadata()
            
            if not metadata.created_at:
                metadata.created_at = now
            
            metadata.last_rotated = now
            metadata.rotation_count += 1
            metadata.expires_at = (
                datetime.now() + timedelta(days=MAX_PASSWORD_AGE_DAYS)
            ).isoformat()
            
            self._save_metadata(metadata)
            
            logger.info("Credentials stored successfully")
            return True, "Inloggegevens succesvol opgeslagen"
            
        except Exception as e:
            logger.error(f"Error storing credentials: {e}")
            return False, f"Fout bij opslaan inloggegevens: {str(e)}"

    def store_credential(self, service: str, key: str, value: str) -> None:
        """Backward-compatible single-value credential storage."""
        current = self._load_credential_bundle()
        current.setdefault(service, {})[key] = value
        self._save_credential_bundle(current)

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Backward-compatible single-value credential retrieval."""
        return self._load_credential_bundle().get(service, {}).get(key)
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieve stored credentials
        
        Returns:
            Tuple of (email, password) or (None, None) if not found
        """
        try:
            if self._fernet and os.path.exists(self._credentials_file):
                with open(self._credentials_file, 'rb') as f:
                    encrypted = f.read()
                
                decrypted = self._fernet.decrypt(encrypted)
                credentials = json.loads(decrypted.decode())
                return credentials.get('email'), credentials.get('password')
            else:
                # Try system keyring
                if keyring is None:
                    return None, None
                email = keyring.get_password(KEYRING_SERVICE, 'email')
                password = keyring.get_password(KEYRING_SERVICE, 'password')
                return email, password
                
        except Exception as e:
            logger.error(f"Error retrieving credentials: {e}")
            return None, None
    
    def rotate_credentials(
        self,
        new_email: Optional[str] = None,
        new_password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Rotate credentials (update email and/or password)
        
        Args:
            new_email: New email address (optional)
            new_password: New password (optional)
            
        Returns:
            Tuple of (success, message)
        """
        current_email, current_password = self.get_credentials()
        
        if not current_email and not new_email:
            return False, "Geen huidige of nieuwe inloggegevens beschikbaar"
        
        email = new_email if new_email else current_email
        password = new_password if new_password else current_password
        
        if not password:
            return False, "Wachtwoord is verplicht"
        
        # Validate new credentials
        is_valid, error = CredentialValidator.validate_credentials(email, password)
        if not is_valid:
            return False, error
        
        # Check password is actually different
        if new_password and new_password == current_password:
            return False, "Nieuw wachtwoord moet verschillen van het huidige"
        
        # Store rotated credentials
        success, message = self.store_credentials(email, password, validate=False)
        
        if success:
            logger.info("Credentials rotated successfully")
            return True, "Inloggegevens succesvol geroteerd"
        
        return success, message
    
    def validate_stored_credentials(self) -> Tuple[bool, str]:
        """
        Validate currently stored credentials
        
        Returns:
            Tuple of (is_valid, message)
        """
        email, password = self.get_credentials()
        
        if not email or not password:
            return False, "Geen inloggegevens gevonden"
        
        is_valid, error = CredentialValidator.validate_credentials(email, password)
        
        # Update metadata
        metadata = self._load_metadata()
        metadata.last_validated = datetime.now().isoformat()
        metadata.validation_status = "valid" if is_valid else "invalid"
        self._save_metadata(metadata)
        
        if is_valid:
            return True, "Inloggegevens zijn geldig"
        
        return False, error
    
    def check_rotation_needed(self) -> Tuple[bool, str]:
        """
        Check if credential rotation is needed
        
        Returns:
            Tuple of (rotation_needed, message)
        """
        metadata = self._load_metadata()
        
        if not metadata.expires_at:
            return True, "Geen vervaldatum ingesteld, rotatie aanbevolen"
        
        try:
            expires_at = datetime.fromisoformat(metadata.expires_at)
            days_until_expiry = (expires_at - datetime.now()).days
            
            if days_until_expiry <= 0:
                return True, "Inloggegevens zijn verlopen, rotatie vereist"
            elif days_until_expiry <= 14:
                return True, f"Inloggegevens verlopen over {days_until_expiry} dagen"
            else:
                return False, f"Inloggegevens geldig tot {expires_at.strftime('%d-%m-%Y')}"
                
        except Exception as e:
            logger.error(f"Error checking rotation: {e}")
            return True, "Kan vervaldatum niet controleren, rotatie aanbevolen"
    
    def delete_credentials(self) -> Tuple[bool, str]:
        """
        Delete stored credentials
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Delete encrypted file
            if os.path.exists(self._credentials_file):
                os.remove(self._credentials_file)
            
            # Delete from keyring
            if keyring is not None:
                try:
                    keyring.delete_password(KEYRING_SERVICE, 'email')
                    keyring.delete_password(KEYRING_SERVICE, 'password')
                except keyring.errors.PasswordDeleteError:
                    pass
            
            # Delete metadata
            if os.path.exists(self._metadata_file):
                os.remove(self._metadata_file)
            
            logger.info("Credentials deleted successfully")
            return True, "Inloggegevens succesvol verwijderd"
            
        except Exception as e:
            logger.error(f"Error deleting credentials: {e}")
            return False, f"Fout bij verwijderen inloggegevens: {str(e)}"
    
    def get_credential_status(self) -> Dict[str, Any]:
        """
        Get comprehensive credential status
        
        Returns:
            Dictionary with credential status information
        """
        metadata = self._load_metadata()
        email, _ = self.get_credentials()
        rotation_needed, rotation_message = self.check_rotation_needed()
        
        return {
            'has_credentials': email is not None,
            'email': email[:3] + '***' + email[email.index('@'):] if email else None,
            'created_at': metadata.created_at,
            'last_rotated': metadata.last_rotated,
            'rotation_count': metadata.rotation_count,
            'last_validated': metadata.last_validated,
            'validation_status': metadata.validation_status,
            'expires_at': metadata.expires_at,
            'rotation_needed': rotation_needed,
            'rotation_message': rotation_message
        }
    
    def _load_metadata(self) -> CredentialMetadata:
        """Load credential metadata"""
        if os.path.exists(self._metadata_file):
            try:
                with open(self._metadata_file, 'r') as f:
                    data = json.load(f)
                return CredentialMetadata.from_dict(data)
            except Exception as e:
                logger.warning(f"Error loading metadata: {e}")
        
        return CredentialMetadata()
    
    def _save_metadata(self, metadata: CredentialMetadata) -> None:
        """Save credential metadata"""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            os.chmod(self._metadata_file, 0o600)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def _load_credential_bundle(self) -> Dict[str, Dict[str, str]]:
        if not self._fernet:
            raise ValueError("Master password is required before using encrypted credential storage")
        if not os.path.exists(self._credentials_file):
            return {}

        with open(self._credentials_file, 'rb') as f:
            encrypted = f.read()
        return json.loads(self._fernet.decrypt(encrypted).decode())

    def _save_credential_bundle(self, data: Dict[str, Dict[str, str]]) -> None:
        if not self._fernet:
            raise ValueError("Master password is required before using encrypted credential storage")
        os.makedirs(os.path.dirname(self._credentials_file) or '.', exist_ok=True)
        encrypted = self._fernet.encrypt(json.dumps(data).encode())
        with open(self._credentials_file, 'wb') as f:
            f.write(encrypted)
        os.chmod(self._credentials_file, 0o600)


# Convenience function for backward compatibility
def get_stored_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Get stored credentials using default manager"""
    manager = SecureCredentialManager()
    return manager.get_credentials()
