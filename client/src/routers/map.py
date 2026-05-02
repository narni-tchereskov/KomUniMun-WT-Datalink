import httpx
import logging
import random

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from time import time

from src.infrastructure.config.settings import Settings
from src.ports.services.encryption_port import EncryptionPort
from src.ports.services.file_loader_port import FileLoaderPort


class MapRouter:
    """Class responsible for handling map endpoint flow and real-time sync."""

    def __init__(
        self,
        settings: Settings,
        encryption: EncryptionPort,
        file_loader: FileLoaderPort,
        httpx_client: httpx.AsyncClient,
    ):
        """
        Defines initial parameters of the class.

        Args:
            settings (Settings): Settings class housing all environment variables.
            encryption (EncryptionPort): Communication encryption system.
            file_loader (FileLoaderPort): System for loading of files.
            httpx_client (httpx.AsyncClient): Communication client for server exchanges.
        """

        self._logger = logging.getLogger(__class__.__name__)

        self._settings = settings
        self._encryption = encryption
        self._file_loader = file_loader
        self._httpx_client = httpx_client

    async def _mock_data(self) -> JSONResponse:
        """Generates a simulated server response for local testing."""

        jitter_x = random.uniform(-5000, 5000)
        jitter_y = random.uniform(-5000, 5000)

        # Simulate different altitudes for testing.
        altitude_player = random.uniform(500, 1000)
        altitude_mock_1 = random.uniform(200, 700)
        altitude_mock_2 = random.uniform(800, 1200)

        fake_players = {
            self._settings.username: {
                "x": 15000 + jitter_x,
                "y": -20000 + jitter_y,
                "compass": random.randint(0, 360),
                "altitude": altitude_player,
            },
            "Mock 1": {
                "x": 5500 - jitter_x,
                "y": -10500 - jitter_y,
                "compass": random.randint(0, 360),
                "altitude": altitude_mock_1,
            },
            "Mock 2": {
                "x": 5500 - jitter_x,
                "y": -20500 - jitter_y,
                "compass": random.randint(0, 360),
                "altitude": altitude_mock_2,
            },
        }

        return JSONResponse(
            {
                "status": f"{len(fake_players)} players",
                "players": fake_players,
                "username": self._settings.username,
            }
        )

    async def _mock_map(self) -> dict:
        """Generates simulated map info for local testing."""

        # Using Sinai grid size.
        return {
            "map_min": [-65536, -65536],
            "map_max": [65536, 65536],
            "grid_steps": [16384, 16384],
            "map_generation": int(time()),
        }

    async def synchronize_data(self, request: Request) -> JSONResponse:
        """Executes the real-time synchronization flow asynchronously."""

        if self._settings.test_mode:
            return await self._mock_data()

        try:
            wt_res = await self._httpx_client.get(
                f"{self._settings.wt_localhost}/state", timeout=2.0
            )
            wt_data = wt_res.json()

            payload_dict = {
                "password": self._settings.session_password,
                "username": self._settings.username,
                "x": wt_data.get("x", 0),
                "y": wt_data.get("y", 0),
                "compass": wt_data.get("compass", 0),
                "altitude": wt_data.get("H, m", 0),
            }

            encrypted_payload = self._encryption.encrypt_data(payload_dict)

            server_res = await self._httpx_client.post(
                f"{self._settings.server}/api/synchronizer",
                json={"payload": encrypted_payload},
                timeout=3.0,
            )

            if server_res.status_code == 200:
                response_json = server_res.json()
                decrypted_response = self._encryption.decrypt_data(
                    response_json.get("payload")
                )

                if decrypted_response:
                    players = decrypted_response.get("players", {})
                    return JSONResponse(
                        {
                            "status": f"Connected: {len(players)} player(s) online",
                            "players": players,
                            "username": self._settings.username,
                        }
                    )
                else:
                    return JSONResponse(
                        {"status": "Error: Server Decryption Failed", "players": {}}
                    )
            else:
                return JSONResponse(
                    {"status": f"Server Error {server_res.status_code}", "players": {}}
                )

        except httpx.RequestError:
            return JSONResponse(
                {"status": "Connection Error (WT or Server Down)", "players": {}}
            )

        except Exception:
            self._logger.error("Unexpected error during sync execution", exc_info=True)
            return JSONResponse({"status": "Internal Sync Error", "players": {}})

    async def get_map_info(self, request: Request) -> JSONResponse:
        """Retrieves map information from localhost."""

        if self._settings.test_mode:
            return JSONResponse(await self._mock_map())

        try:
            wt_res = await self._httpx_client.get(
                f"{self._settings.wt_localhost}/map_info.json", timeout=2.0
            )
            wt_res.raise_for_status()
            return JSONResponse(wt_res.json())

        except Exception:
            self._logger.error(
                "Failed to get map_info.json",
                exc_info=True,
            )
            # Fallback to prevent UI lockup.
            return JSONResponse(
                {
                    "map_min": [-65536, -65536],
                    "map_max": [65536, 65536],
                    "grid_steps": [16384, 16384],
                }
            )

    async def display_map(self, request: Request) -> HTMLResponse:
        """Displays the real time map from synchronized data."""

        html_content = await self._file_loader.get_file("map_template.html")
        return HTMLResponse(html_content)
