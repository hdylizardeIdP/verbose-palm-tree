"""
Token encryption utilities for secure OAuth token storage.

This module provides encryption/decryption for OAuth tokens using Fernet
symmetric encryption (AES-128-CBC with HMAC-SHA256).

Security considerations:
- Encryption key should be stored securely (environment variable, key vault)
- Never commit encryption keys to version control
- Rotate keys periodically
- Old encrypted tokens become invalid after key rotation
"""
import os
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# File extension for encrypted token files
ENCRYPTED_EXTENSION = ".encrypted"


class TokenEncryptionError(Exception):
    """Exception raised for token encryption/decryption errors."""
    pass


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize token encryption.

        Args:
            encryption_key: Base64-encoded Fernet key or passphrase.
                           If None, attempts to load from SCHWAB_TOKEN_ENCRYPTION_KEY env var.

        Raises:
            TokenEncryptionError: If no encryption key is available.
        """
        key_source = encryption_key or os.getenv("SCHWAB_TOKEN_ENCRYPTION_KEY")

        if not key_source:
            raise TokenEncryptionError(
                "No encryption key provided. Set SCHWAB_TOKEN_ENCRYPTION_KEY environment variable "
                "or pass encryption_key parameter. Generate a key with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        self._fernet = self._create_fernet(key_source)

    def _create_fernet(self, key_source: str) -> Fernet:
        """
        Create a Fernet instance from a key source.

        Args:
            key_source: Either a valid Fernet key (44 chars base64) or a passphrase.

        Returns:
            Fernet instance for encryption/decryption.
        """
        # Try to use as direct Fernet key first
        try:
            # Valid Fernet keys are 44 characters of URL-safe base64
            if len(key_source) == 44:
                return Fernet(key_source.encode())
        except Exception:
            pass

        # Derive a key from the passphrase using PBKDF2
        # Use a fixed salt for deterministic key derivation
        # In production, consider storing salt separately
        salt = b"schwab_token_encryption_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_source.encode()))
        return Fernet(key)

    def encrypt_tokens(self, token_data: Dict[str, Any]) -> bytes:
        """
        Encrypt token data.

        Args:
            token_data: Dictionary containing OAuth tokens.

        Returns:
            Encrypted bytes.

        Raises:
            TokenEncryptionError: If encryption fails.
        """
        try:
            json_data = json.dumps(token_data).encode('utf-8')
            encrypted = self._fernet.encrypt(json_data)
            return encrypted
        except Exception as e:
            logger.error("Failed to encrypt tokens")
            raise TokenEncryptionError(f"Encryption failed: {type(e).__name__}")

    def decrypt_tokens(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        Decrypt token data.

        Args:
            encrypted_data: Encrypted bytes.

        Returns:
            Dictionary containing OAuth tokens.

        Raises:
            TokenEncryptionError: If decryption fails (wrong key, corrupted data, etc.).
        """
        try:
            decrypted = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except InvalidToken:
            logger.error("Invalid encryption key or corrupted token file")
            raise TokenEncryptionError(
                "Failed to decrypt tokens. The encryption key may be incorrect "
                "or the token file may be corrupted."
            )
        except json.JSONDecodeError:
            logger.error("Decrypted data is not valid JSON")
            raise TokenEncryptionError("Decrypted token data is not valid JSON")
        except Exception as e:
            logger.error("Failed to decrypt tokens")
            raise TokenEncryptionError(f"Decryption failed: {type(e).__name__}")

    def save_encrypted_tokens(self, token_data: Dict[str, Any], file_path: Path) -> None:
        """
        Encrypt and save tokens to a file.

        Args:
            token_data: Dictionary containing OAuth tokens.
            file_path: Path to save encrypted tokens.

        Raises:
            TokenEncryptionError: If encryption or file write fails.
        """
        try:
            encrypted = self.encrypt_tokens(token_data)

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write with restrictive permissions (owner read/write only)
            with open(file_path, 'wb') as f:
                f.write(encrypted)

            # Set file permissions to 600 (owner read/write only)
            try:
                os.chmod(file_path, 0o600)
            except OSError:
                # May fail on some systems (e.g., Windows)
                logger.warning("Could not set restrictive file permissions")

            logger.info(f"Encrypted tokens saved to {file_path}")
        except TokenEncryptionError:
            raise
        except Exception as e:
            logger.error(f"Failed to save encrypted tokens: {type(e).__name__}")
            raise TokenEncryptionError(f"Failed to save tokens: {type(e).__name__}")

    def load_encrypted_tokens(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and decrypt tokens from a file.

        Args:
            file_path: Path to encrypted token file.

        Returns:
            Dictionary containing OAuth tokens.

        Raises:
            TokenEncryptionError: If file read or decryption fails.
            FileNotFoundError: If the token file doesn't exist.
        """
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            return self.decrypt_tokens(encrypted_data)
        except FileNotFoundError:
            raise
        except TokenEncryptionError:
            raise
        except Exception as e:
            logger.error(f"Failed to load encrypted tokens: {type(e).__name__}")
            raise TokenEncryptionError(f"Failed to load tokens: {type(e).__name__}")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded Fernet key suitable for SCHWAB_TOKEN_ENCRYPTION_KEY.
    """
    return Fernet.generate_key().decode()


def is_encrypted_token_file(file_path: Path) -> bool:
    """
    Check if a token file appears to be encrypted.

    Args:
        file_path: Path to token file.

    Returns:
        True if the file appears to be encrypted (not valid JSON).
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # Try to parse as JSON (plain text token file)
        try:
            json.loads(content.decode('utf-8'))
            return False  # Valid JSON = not encrypted
        except (json.JSONDecodeError, UnicodeDecodeError):
            return True  # Not valid JSON = likely encrypted
    except FileNotFoundError:
        return False


def migrate_plain_text_tokens(
    plain_text_path: Path,
    encrypted_path: Path,
    encryption: TokenEncryption,
    delete_original: bool = False
) -> bool:
    """
    Migrate plain text token file to encrypted format.

    Args:
        plain_text_path: Path to existing plain text token file.
        encrypted_path: Path for new encrypted token file.
        encryption: TokenEncryption instance with key configured.
        delete_original: If True, delete the plain text file after migration.

    Returns:
        True if migration was successful.

    Raises:
        TokenEncryptionError: If migration fails.
    """
    if not plain_text_path.exists():
        logger.info("No plain text token file to migrate")
        return False

    try:
        # Read plain text tokens
        with open(plain_text_path, 'r') as f:
            token_data = json.load(f)

        logger.info(f"Migrating tokens from {plain_text_path} to encrypted format")

        # Save encrypted
        encryption.save_encrypted_tokens(token_data, encrypted_path)

        # Optionally delete original
        if delete_original:
            plain_text_path.unlink()
            logger.info(f"Deleted plain text token file: {plain_text_path}")
        else:
            logger.warning(
                f"Plain text token file still exists at {plain_text_path}. "
                "Consider deleting it for security."
            )

        return True
    except json.JSONDecodeError:
        raise TokenEncryptionError(
            f"Plain text token file at {plain_text_path} is not valid JSON"
        )
    except Exception as e:
        raise TokenEncryptionError(f"Migration failed: {type(e).__name__}: {e}")
