from abc import ABC, abstractmethod
from typing import Any


class HandshakeValidatorPort(ABC):
    """Port defining an adapter contract for asymmetrical cryptographic operations."""

    @abstractmethod
    def verify_signature(
        self,
        username: str,
        payload: dict[Any, Any],
        signature: str,
    ) -> bool:
        """
        Verifies the signature in a request sent to the server.

        Args:
            username (str): Username extracted from the file.
            payload (dict[Any, Any]): The data dictionary to sign.
            signature (str): Signature provided in the request.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()
