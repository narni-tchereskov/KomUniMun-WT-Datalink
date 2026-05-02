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

    port: int = 5000

    encryption_seed: str = "seed"
    session_password: str = "password"

    public_key_folder: str = "./public_keys"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore
