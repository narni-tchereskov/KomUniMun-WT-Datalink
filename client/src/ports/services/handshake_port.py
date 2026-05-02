from abc import ABC, abstractmethod
from typing import Any


class HandshakePort(ABC):
    """Port defining an adapter contract for asymmetrical cryptographic operations."""

    @abstractmethod
    def sign_payload(self, payload: dict[Any, Any]) -> str:
        """
        Signs a dictionary payload to validate the identity of a client.

        Args:
            payload (dict[Any, Any]): The data dictionary to sign.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()
