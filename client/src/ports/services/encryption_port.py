from abc import ABC, abstractmethod
from typing import Any


class EncryptionPort(ABC):
    """Port defining an adapter contract for encryption of communications."""

    @abstractmethod
    def encrypt_data(self, raw_data: dict[Any, Any]) -> str:
        """
        Encrypts the communications dictionary into a URL safe string.

        Args:
            raw_data (dict[Any, Any]): The dictionary containing communication data.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()

    @abstractmethod
    def decrypt_data(self, encrypted_data: str) -> dict | None:
        """
        Decrypts the encypted URL safe string data into a dictionary.

        Args:
            encrypted_data (str): The encrypted data in string format.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()
