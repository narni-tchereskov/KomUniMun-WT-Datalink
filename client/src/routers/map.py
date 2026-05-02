import asyncio
import base64
import httpx
import logging
import random

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
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

    def _get_fallback(self) -> dict:
        """Returns a generic map configuration when not connected to localhost."""

        return {
            "map_min": [-65536, -65536],
            "map_max": [65536, 65536],
            "grid_steps": [16384, 16384],
            "map_generation": 0,
        }

    async def _mock_data(self) -> JSONResponse:
        """Generates a simulated server response for local testing."""

        jitter_x = random.uniform(-0.01, 0.01)
        jitter_y = random.uniform(-0.01, 0.01)

        fake_players = {
            self._settings.username: {
                "x": 0.5 + jitter_x,
                "y": 0.5 + jitter_y,
                "compass": random.randint(0, 360),
                "altitude": random.uniform(500, 1000),
            },
            "Mock": {
                "x": 0.55 - jitter_x,
                "y": 0.45 - jitter_y,
                "compass": random.randint(0, 360),
                "altitude": random.uniform(500, 1000),
            },
        }

        return JSONResponse(
            {
                "status": f"{len(fake_players)} players",
                "players": fake_players,
                "username": self._settings.username,
                "map_generation": int(time()),
            }
        )

    async def _mock_map(self) -> dict:
        """Generates simulated map info for local testing."""

        return {
            "map_min": [-65536, -65536],
            "map_max": [65536, 65536],
            "grid_steps": [8192, 8192],
            "map_generation": int(time()),
        }

    async def get_background(self, request: Request) -> Response:
        """Gets the background map image from localhost."""

        if self._settings.test_mode:
            # Prevents missing image error during test.
            transparent_pixel = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            )
            return Response(content=transparent_pixel, media_type="image/png")

        try:
            gen = request.query_params.get("gen", "")
            url = f"{self._settings.wt_localhost}/map.img"
            if gen:
                url += f"?gen={gen}"

            wt_res = await self._httpx_client.get(url, timeout=2.0)
            wt_res.raise_for_status()

            return Response(content=wt_res.content, media_type="image/jpeg")

        except Exception:
            self._logger.error(
                "Failed to fetch map image",
                exc_info=True,
            )
            return Response(status_code=404)

    async def synchronize_data(self, request: Request) -> JSONResponse:
        """Executes the real-time synchronization flow asynchronously."""

        if self._settings.test_mode:
            return await self._mock_data()

        try:
            req_state = self._httpx_client.get(
                f"{self._settings.wt_localhost}/state", timeout=2.0
            )
            req_objs = self._httpx_client.get(
                f"{self._settings.wt_localhost}/map_obj.json", timeout=2.0
            )
            req_info = self._httpx_client.get(
                f"{self._settings.wt_localhost}/map_info.json", timeout=2.0
            )
            req_indicators = self._httpx_client.get(
                f"{self._settings.wt_localhost}/indicators", timeout=2.0
            )

            res_state, res_objs, res_info, res_indicators = await asyncio.gather(
                req_state, req_objs, req_info, req_indicators
            )

            wt_state = res_state.json()
            wt_objs = res_objs.json()
            wt_info = res_info.json()
            wt_indicators = res_indicators.json()

            if not wt_state.get("valid", False):
                return JSONResponse(
                    {
                        "status": "Waiting for data",
                        "players": {},
                        "map_generation": 0,
                    }
                )

            player_x, player_y = 0.0, 0.0

            for obj in wt_objs:
                if obj.get("icon") == "Player":
                    player_x = obj.get("x", 0.0)
                    player_y = obj.get("y", 0.0)
                    break

            payload_dict = {
                "password": self._settings.session_password,
                "username": self._settings.username,
                "x": player_x,
                "y": player_y,
                "compass": wt_indicators.get("compass", 0),
                "altitude": wt_state.get("H, m", 0),
            }

            encrypted_payload = self._encryption.encrypt_data(payload_dict)

            server_res = await self._httpx_client.post(
                f"{self._settings.server}/api/synchronizer",
                json={"payload": encrypted_payload},
                timeout=3.0,
            )

            map_gen = wt_info.get("map_generation", 0)

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
                            "map_generation": map_gen,
                        },
                    )

            return JSONResponse(
                {
                    "status": "Synchronization failed",
                    "players": {},
                    "map_generation": map_gen,
                },
            )

        except (httpx.ConnectError, httpx.ReadTimeout):
            return JSONResponse(
                {
                    "status": "Localhost disconnected",
                    "players": {},
                    "map_generation": 0,
                },
            )

        except Exception:
            self._logger.error(
                "Unexpected error during sync execution",
                exc_info=True,
            )
            return JSONResponse(
                {
                    "status": "Internal Sync Error",
                    "players": {},
                    "map_generation": 0,
                },
            )

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

        except (httpx.ConnectError, httpx.ReadTimeout):
            self._logger.error(
                "Using fallback data",
                exc_info=True,
            )
            return JSONResponse(self._get_fallback())

        except Exception:
            self._logger.error(
                "Unknown error fetching map_info.json",
                exc_info=True,
            )
            # Fallback to prevent UI lockup.
            return JSONResponse(self._get_fallback())

    async def display_map(self, request: Request) -> HTMLResponse:
        """Displays the real time map from synchronized data."""

        html_content = await self._file_loader.get_file("map_template.html")
        return HTMLResponse(html_content)
