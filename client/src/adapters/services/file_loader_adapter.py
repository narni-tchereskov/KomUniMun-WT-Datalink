import asyncio
import logging
import sys

from async_lru import alru_cache
from pathlib import Path

from src.ports.services.file_loader_port import FileLoaderPort
from src.domain.exceptions.operation_exceptions import ConfigurationError, LoadError


class FileLoaderAdapter(FileLoaderPort):
    """Class responsible for loading files as strings."""

    def __init__(self, file_directory: str | Path | None = None):
        """
        Defines initial parameters of the class.

        Args:
            file_directory (str | Path | None): File directory, overwrites the default.

        Raises:
            ConfigurationError: If the file directory does not exist.
        """

        self._logger = logging.getLogger(__class__.__name__)

        if file_directory:
            self._file_directory = Path(file_directory)

        else:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                self._file_directory = (
                    Path(sys._MEIPASS) / "src" / "infrastructure" / "templates"  # type: ignore
                )
            else:
                self._file_directory = (
                    Path(__file__).parent.parent.parent / "infrastructure" / "templates"
                )

        if not self._file_directory.is_dir():
            self._logger.error(
                "File directory does not exist",
                extra={"directory": str(self._file_directory)},
                exc_info=True,
            )
            raise ConfigurationError("File directory does not exist")

        self._logger.info(
            "File loading system initialized",
            extra={"directory": str(self._file_directory)},
        )

    @alru_cache(maxsize=32)
    async def _load_file(self, file_path: Path) -> str:
        """
        Helper method to read a file from a path.

        Args:
            file_path (str | Path): The absolute path to the file.

        Returns:
            The file content as a string.

        Raises:
            LoadError: If the file could not be loaded.
        """

        try:
            return await asyncio.to_thread(file_path.read_text, encoding="utf-8")

        except FileNotFoundError as e:
            self._logger.error(
                "File not found",
                extra={"file_path": str(file_path)},
                exc_info=True,
            )
            raise LoadError("File not found") from e

        except Exception as e:
            self._logger.error(
                "Unknown error during file loading",
                extra={"file_path": str(file_path)},
                exc_info=True,
            )
            raise LoadError("Unknown error during file loading") from e

    async def preload_files(self):
        """Method for preloading all files into cache."""

        files = [file for file in self._file_directory.iterdir() if file.is_file()]

        if not files:
            self._logger.warning("No files to preload")
            return

        self._logger.info("Preloading file(s)...", extra={"count": len(files)})

        tasks = [self._load_file(file_path) for file_path in files]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for file_path, result in zip(files, results):
            if isinstance(result, Exception):
                self._logger.error(
                    "Failed to preload file",
                    extra={
                        "filename": file_path.name,
                        "error": str(result),
                    },
                )

        self._logger.info("Files preloaded successfully")

    async def get_file(self, filename: str) -> str:
        """
        Method for getting a file by the full filename.

        Args:
            filename(str): Full name including extension of the file to load.

        Returns:
            The content of the file as a string.
        """

        # Only performs the actual read if it was not in cache.
        return await self._load_file(self._file_directory / filename)
