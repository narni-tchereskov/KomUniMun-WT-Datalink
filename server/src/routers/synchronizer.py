import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from time import time

from src.infrastructure.config.settings import Settings
from src.ports.services.encryption_port import EncryptionPort
from src.ports.services.handshake_validator_port import HandshakeValidatorPort


class SynchronizerRouter:
    """Handles authentication and real-time coordinate synchronization."""

    def __init__(
        self,
        settings: Settings,
        encryption: EncryptionPort,
        handshake_validator: HandshakeValidatorPort,
    ):
        """
        Defines initial parameters of the class.

        Args:
            settings (Settings): Settings class housing all environment variables.
            encryption (EncryptionPort): Communication encryption system.
            handshake_validator (HandshakeValidatorPort): Handshake validation system.
        """

        self._logger = logging.getLogger(__class__.__name__)

        self._settings = settings
        self._encryption = encryption
        self._handshake_validator = handshake_validator

        self._authenticated_users = {}
        self._active_players = {}

    async def authenticate_client(self, request: Request) -> JSONResponse:
        """Validates a handshake request sent to the server."""

        try:
            body = await request.json()
            payload = body.get("payload", {})
            signature = body.get("signature", "")
            username = payload.get("username")

            # Validates timestamp to avoid stale requests.
            client_time = payload.get("timestamp", 0)
            if abs(time() - client_time) > 60:
                return JSONResponse(
                    {
                        "status": "error",
                        "message": "Timestamp expired",
                    },
                    status_code=401,
                )

            # Initial handshake validation.
            if self._handshake_validator.verify_signature(username, payload, signature):
                self._authenticated_users[username] = time()
                self._logger.info(
                    "User authenticated",
                    extra={"username": username},
                )
                return JSONResponse({"status": "success"})

            return JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid signature",
                },
                status_code=401,
            )

        except Exception:
            self._logger.error(
                "Bad handshake",
                exc_info=True,
            )
            return JSONResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                },
                status_code=400,
            )

    async def synchronize_data(self, request: Request) -> JSONResponse:
        """Synchronizes playerp positions through requests."""

        try:
            body = await request.json()
            encrypted_payload = body.get("payload")

            if not encrypted_payload:
                return JSONResponse(
                    {"status": "error"},
                    status_code=400,
                )

            # Symmetric rolling decryption.
            data = self._encryption.decrypt_data(encrypted_payload)

            if not data or data.get("password") != self._settings.session_password:
                return JSONResponse(
                    {"status": "unauthorized"},
                    status_code=401,
                )

            username = data.get("username")

            if username not in self._authenticated_users:
                self._logger.warning(
                    "Unauthenticated synchronization attempt",
                    extra={"username": username},
                )
                return JSONResponse(
                    {
                        "status": "unauthorized",
                        "message": "Handshake required",
                    },
                    status_code=401,
                )

            # Updates state on the server & remove stale connections.
            current_time = time()
            self._active_players[username] = {
                "x": data.get("x", 0),
                "y": data.get("y", 0),
                "compass": data.get("compass", 0),
                "altitude": data.get("altitude", 0),
                "last_seen": current_time,
            }

            stale_players = [
                player
                for player, player_data in self._active_players.items()
                if current_time - player_data["last_seen"] > 30
            ]
            for player in stale_players:
                del self._active_players[player]

            clean_players = {
                key: {
                    "x": value["x"],
                    "y": value["y"],
                    "compass": value["compass"],
                    "altitude": value["altitude"],
                }
                for key, value in self._active_players.items()
            }

            response_payload = self._encryption.encrypt_data({"players": clean_players})
            return JSONResponse({"payload": response_payload})

        except Exception:
            self._logger.error(
                "Synchronization error",
                exc_info=True,
            )
            return JSONResponse(
                {"status": "error"},
                status_code=500,
            )
