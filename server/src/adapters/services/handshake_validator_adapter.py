import base64
import json
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from pathlib import Path
from typing import Any

from src.ports.services.handshake_validator_port import HandshakeValidatorPort


class HandshakeValidatorAdapter(HandshakeValidatorPort):
    """Class responsible for validating handshakes using public keys."""

    def __init__(self, keys_folder_path: str | Path):
        """
        Defines initial parameters of the class.

        Args:
            keys_folder_path (str | Path): Path to the folder with public .pem files.

        Raises:
            ConfigurationError: If the key file is missing, invalid, or not an RSA key.
            OperationError: For unknown errors during key loading.
        """

        self._logger = logging.getLogger(__class__.__name__)

        self._keys_folder = Path(keys_folder_path)
        self._public_keys = {}

        if not self._keys_folder.is_dir():
            self._logger.warning(
                "Public keys folder does not exist",
                extra={"folder": str(self._keys_folder)},
            )

            self._logger.info("Creating keys folder...")
            self._keys_folder.mkdir(parents=True, exist_ok=True)
            self._logger.info("Keys folder created")

        self._load_all_keys()

    def _load_all_keys(self):
        """Loads all .pem and .pub files by filename into memory."""

        count = 0

        for key_file in self._keys_folder.iterdir():
            if key_file.is_file() and key_file.suffix in [".pem", ".pub"]:
                try:
                    # Username is the filename without the file extension.
                    username = key_file.stem
                    key_data = key_file.read_bytes()
                    self._public_keys[username] = load_pem_public_key(key_data)
                    count += 1

                except Exception:
                    self._logger.error(
                        "Failed to load public key",
                        extra={"filename": key_file.name},
                        exc_info=True,
                    )

        self._logger.info("Public keys loaded into memory", extra={"count": count})

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

        Returns:
            A bool which describes the signature's validity.
        """

        public_key = self._public_keys.get(username)

        if not public_key:
            self._logger.warning(
                "Verification failed",
                extra={"username": username},
            )
            return False

        try:
            sign_bytes = base64.urlsafe_b64decode(signature)
            json_data = json.dumps(payload, sort_keys=True).encode("utf-8")

            public_key.verify(
                signature=sign_bytes,
                data=json_data,
                padding=padding.PSS(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                algorithm=hashes.SHA256(),
            )

            return True

        except InvalidSignature:
            self._logger.warning(
                "Invalid digital signature received",
                extra={"username": username},
            )
            return False

        except Exception:
            self._logger.error(
                "Unknown error during signature verification",
                extra={"username": username},
                exc_info=True,
            )
            return False
