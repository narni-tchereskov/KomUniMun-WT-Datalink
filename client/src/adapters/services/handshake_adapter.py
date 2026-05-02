import base64
import json
import logging

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pathlib import Path
from typing import Any

from src.domain.exceptions.operation_exceptions import (
    ConfigurationError,
    OperationError,
)
from src.ports.services.handshake_port import HandshakePort


class HandshakeAdapter(HandshakePort):
    """Class responsible for handshake operation using asymmetric keys."""

    def __init__(self, private_key_path: str | Path, key_password: bytes | None = None):
        """
        Defines initial parameters of the class.

        Args:
            private_key_path (str | Path): Path to the private .pem file.
            key_password (bytes | None): Password to decrypt the .pem file if encrypted.

        Raises:
            ConfigurationError: If the key file is missing, invalid, or not an RSA key.
            OperationError: For unknown errors during key loading.
        """

        self._logger = logging.getLogger(__class__.__name__)

        self._key_file = Path(private_key_path)

        if not self._key_file.is_file():
            self._logger.error(
                "Asymmetrical private key file not found",
                extra={"file_path": str(self._key_file)},
                exc_info=True,
            )
            raise ConfigurationError("Asymmetrical private key file not found")

        try:
            self._pem_data = self._key_file.read_bytes()
            self._loaded_key = load_pem_private_key(
                data=self._pem_data,
                password=key_password,
            )

            if not isinstance(self._loaded_key, rsa.RSAPrivateKey):
                self._logger.error(
                    "Loaded key has unexpected format",
                    extra={"key_type": type(self._loaded_key).__name__},
                )
                raise ConfigurationError("Loaded key has unexpected format")

            self._private_key = self._loaded_key
            self._logger.info("Asymmetrical RSA private key loaded")

        except ValueError as e:
            self._logger.error(
                "Invalid private key format or password",
                exc_info=True,
            )
            raise ConfigurationError("Invalid private key format or password") from e

        except UnsupportedAlgorithm as e:
            self._logger.error(
                "Unsupported key algorithm",
                exc_info=True,
            )
            raise ConfigurationError("Unsupported key algorithm") from e

        except ConfigurationError:
            raise  # Avoids catching this in the Exception block.

        except Exception as e:
            self._logger.error(
                "Unknown error during key read operation",
                exc_info=True,
            )
            raise OperationError("Unknown error during key read operation") from e

    def sign_payload(self, payload: dict[Any, Any]) -> str:
        """
        Signs a dictionary payload to validate the identity of a client.

        Args:
            payload (dict[Any, Any]): The data dictionary to sign.

        Returns:
            A URL safe Base64 encoded digital signature.

        Raises:
            OperationError: If signing fails.
        """

        try:
            json_data = json.dumps(payload, sort_keys=True).encode("utf-8")

            signature = self._private_key.sign(
                data=json_data,
                padding=padding.PSS(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                algorithm=hashes.SHA256(),
            )

            return base64.urlsafe_b64encode(signature).decode("utf-8")

        except Exception as e:
            self._logger.error(
                "Failed to sign payload",
                exc_info=True,
            )
            raise OperationError("Failed to sign payload") from e
