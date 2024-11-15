import os
from pathlib import Path
from typing import Dict, Optional, Union

import tomli
import tomli_w
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from cobo_cli.data.environments import EnvironmentType

default_manifest_file = "manifest.json"

user_access_token_key = "user_access_token"
org_access_token_key = "org_access_token"


def get_config_path() -> str:
    return str(Path.home() / ".cobo")


class CoboSettings(BaseSettings):
    environment: str = Field(..., env="COBO_ENVIRONMENT")
    auth_method: str = Field(..., env="COBO_AUTH_METHOD")
    api_key: Optional[str] = Field(None, env="COBO_API_KEY")
    api_secret: Optional[str] = Field(None, env="COBO_API_SECRET")
    org_access_token: Optional[str] = Field(None, env="COBO_ORG_ACCESS_TOKEN")
    user_access_token: Optional[str] = Field(None, env="COBO_USER_ACCESS_TOKEN")
    api_host: Optional[str] = Field(None, env="COBO_API_HOST")
    websocket_host: Optional[str] = Field(None, env="COBO_WEBSOCKET_HOST")
    base_url: Optional[str] = Field(None, env="COBO_BASE_URL")

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="allow")

    @field_validator("environment")
    def validate_environment(cls, v):
        if v not in {"sandbox", "dev", "prod"}:
            raise ValueError("Environment must be one of 'sandbox', 'dev', 'prod'")
        return v

    @field_validator("auth_method")
    def validate_auth_method(cls, v):
        if v not in {"apikey", "org", "user"}:
            raise ValueError("Auth method must be one of 'apikey', 'org', 'user'")
        return v


class ConfigManager:
    def __init__(self, config_file: str = None, env_type: str = None):
        self.config_file = config_file if config_file else self.get_config_file_path()

        if not os.path.exists(self.config_file):
            self.create_default_config()

        if env_type is not None and env_type not in EnvironmentType.values():
            raise Exception(f"Invalid env type: {env_type}")
        self.env_type = env_type
        self.config_data = self.load_config_data()
        self.settings = self.load_settings()

    @classmethod
    def get_config_file_path(cls):
        return os.path.join(get_config_path(), "config.toml")

    def load_config_data(self) -> Dict:
        try:
            with open(self.config_file, "rb") as f:
                return tomli.load(f)
        except Exception as e:
            raise Exception(f"Failed to load config file: {e}")

    def load_settings(self):
        common_config = self.config_data.get("common", {})
        env_config = self.config_data.get(
            self.env_type or common_config.get("environment", "dev"), {}
        )
        combined_config = {**common_config, **env_config}
        return CoboSettings.model_validate(combined_config)

    def create_default_config(self):
        default_config = """
[common]
auth_method = "apikey"
environment = "dev"

[sandbox]
api_host = "https://api.sandbox.cobo.com"
websocket_host = "wss://api.sandbox.cobo.com"
base_url = "https://portal.sandbox.cobo.com"

[dev]
api_host = "https://api.dev.cobo.com"
websocket_host = "wss://api.dev.cobo.com"
base_url = "https://portal.dev.cobo.com"

[prod]
api_host = "https://api.cobo.com"
websocket_host = "wss://api.cobo.com"
base_url = "https://portal.cobo.com"
"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            f.write(default_config)

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "wb") as f:
            tomli_w.dump(self.config_data, f)

    def set_config(self, key: str, value: str) -> bool:
        if key in ["environment", "auth_method"]:
            self.config_data["common"][key] = value
        else:
            current_env = self.config_data["common"]["environment"]
            if current_env not in self.config_data:
                self.config_data[current_env] = {}
            self.config_data[current_env][key] = value

        self.save_config()
        self.settings = self.load_settings()
        return True

    def get_config(self, key: str, default: str = None) -> Union[str, None]:
        value = getattr(self.settings, key, None)
        return value if value is not None else default

    def list_configs(self) -> dict:
        return self.settings.model_dump(exclude_none=True)

    def delete_config(self, key: str) -> bool:
        if key in ["environment", "auth_method"]:
            return False  # Don't allow deletion of these keys
        current_env = self.config_data["common"]["environment"]
        if key in self.config_data[current_env]:
            del self.config_data[current_env][key]
            self.save_config()
            self.settings = self.load_settings()
            return True
        return False
