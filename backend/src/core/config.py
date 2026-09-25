from typing import Annotated, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "UK Support"
    app_version: str = "0.1.0"
    debug: bool = False

    database_user: str
    database_password: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str

    bot_token: str = ""
    bot_mode: Literal["polling", "off"] = "off"

    secret_key: str
    storage_dir: str = "storage"

    dev_auth: bool = False
    auth_token_expire_days: int = 30
    admin_max_user_ids: Annotated[list[int], NoDecode] = []

    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("admin_max_user_ids", mode="before")
    @classmethod
    def _parse_admin_max_user_ids(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _validate_bot_token(self) -> Self:
        if self.bot_mode == "polling" and not self.bot_token:
            raise ValueError("BOT_TOKEN must be set when BOT_MODE=polling")
        return self

    @model_validator(mode="after")
    def _validate_secret_key(self) -> Self:
        if not self.debug and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters when DEBUG=false")
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


settings = Settings()
