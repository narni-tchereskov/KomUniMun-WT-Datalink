import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timezone, timedelta
from typing import Any

from src.domain.exceptions.operation_exceptions import (
    ConfigurationError,
    OperationError,
)
from src.ports.services.encryption_port import EncryptionPort


class EncryptionAdapter(EncryptionPort):
    """Class responsible for encrypting server communications."""

    def __init__(self, seed: str):
        """
        Defines initial parameters of the class.

        Args:
            seed (str): Encryption seed.

        Raises:
            ConfigurationError: When the seed is undefined or empty.
        """
        self._logger = logging.getLogger(__class__.__name__)

        if not seed:
            self._logger.error(
                "Encryption seed is missing or empty",
                exc_info=True,
            )
            raise ConfigurationError("Encryption seed is undefined")

        self._seed = seed

        self._logger.info("Encryption system initialized")

    def _get_key(self, offset: int = 0) -> bytes:
        """
        Method responsible for getting an encryption key which changes frequently.

        Args:
            offset (int): Offset in minutes to apply to the current time.

        Returns:
            The encryption key in bytes.
        """

        target_time = datetime.now(timezone.utc) + timedelta(minutes=offset)
        time_value = int(target_time.strftime("%Y%m%d%H%M"))

        input_data = f"{self._seed}_{time_value}".encode()
        key_bytes = hashlib.sha256(input_data).digest()

        return base64.urlsafe_b64encode(key_bytes)

    def encrypt_data(self, raw_data: dict[Any, Any]) -> str:
        """
        Encrypts the communications dictionary into a URL safe string.

        Args:
            raw_data (dict[Any, Any]): The dictionary containing communication data.

        Returns:
            A string with the encoded data.

        Raises:
            OperationError: When encryption operation fails.
        """

        try:
            fernet = Fernet(self._get_key())
            json_data = json.dumps(raw_data).encode()

            return fernet.encrypt(json_data).decode()

        except Exception as e:
            self._logger.error(
                "Unknown error during data encryption",
                exc_info=True,
            )
            raise OperationError("Unknown error during data encryption") from e

    def decrypt_data(self, encrypted_data: str) -> dict | None:
        """
        Decrypts the encypted URL safe string data into a dictionary.

        Args:
            encrypted_data (str): The encrypted data in string format.

        Returns:
            A dictionary with the unencrypted data or nothing.
        """

        # Offsets the minute timer as a failsafe.
        for offset in (-1, 0, 1):
            try:
                fernet = Fernet(self._get_key(offset))
                decrypted = fernet.decrypt(encrypted_data.encode(), ttl=65)
                return json.loads(decrypted.decode())

            except InvalidToken:
                continue

            except Exception:
                self._logger.error(
                    "Unknown error during data decryption",
                    extra={"offset": offset},
                    exc_info=True,
                )
                return None

        return None
