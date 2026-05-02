from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Class housing the environment variables of the project."""

    model_config = SettingsConfigDict(
        frozen=True,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    test_mode: bool = False

    server: str = ""

    username: str = "Player"
    wt_localhost: str = "http://localhost:8111"
    local_map_port: int = 16222

    encryption_seed: str = "seed"
    session_password: str = "password"

    private_key_path: str = ""
    private_key_password: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore
