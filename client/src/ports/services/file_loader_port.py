from abc import ABC, abstractmethod


class FileLoaderPort(ABC):
    """Port defining an adapter contract for file loading."""

    @abstractmethod
    async def preload_files(self):
        """
        Method for preloading all files into cache.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()

    @abstractmethod
    async def get_file(self, filename: str) -> str:
        """
        Method for getting a file by the full filename.

        Args:
            filename(str): Full name including extension of the file to load.

        Raises:
            NotImplementedError: When the method is called but not implemented.
        """

        raise NotImplementedError()
