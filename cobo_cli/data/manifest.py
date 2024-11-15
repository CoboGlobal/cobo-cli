import os
from enum import Enum
from typing import List, Optional

import yaml
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.frameworks import FrameworkEnum
from cobo_cli.utils.config import default_manifest_file


# Define the enum for grant_dimension
class GrantDimensionEnum(str, Enum):
    ORG = "org"
    USER = "user"


# Define the tuple separately
class Manifest(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=30)
    app_id: Optional[str] = ""
    dev_app_id: Optional[str] = ""
    client_id: Optional[str] = ""
    dev_client_id: Optional[str] = ""
    callback_urls: List[HttpUrl] = Field(default_factory=list)
    app_desc: str = Field(..., max_length=80)
    app_icon_url: HttpUrl
    homepage_url: HttpUrl
    policy_url: Optional[HttpUrl] = None
    app_key: str = Field(..., max_length=80, serialization_alias="client_key")
    app_desc_long: str = Field(..., max_length=1000)
    tags: List[str] = Field(default_factory=list)
    screen_shots: List[HttpUrl] = Field(default_factory=list)
    creator_name: str
    contact_email: EmailStr
    support_site_url: HttpUrl
    permission_notice: Optional[str] = None
    required_permissions: List[str] = Field(default_factory=list)
    optional_permissions: List[str] = Field(default_factory=list)
    framework: Optional[FrameworkEnum] = None
    allow_multiple_tokens: Optional[bool] = False
    grant_dimension: Optional[GrantDimensionEnum] = GrantDimensionEnum.ORG

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    def check_required_fields(self) -> "Manifest":
        required_fields = [
            "app_name",
            "callback_urls",
            "app_key",
            "creator_name",
            "app_desc",
            "app_icon_url",
            "homepage_url",
            "contact_email",
            "support_site_url",
            "screen_shots",
            "app_desc_long",
            "required_permissions",
        ]
        missing_fields = [
            field for field in required_fields if not getattr(self, field)
        ]
        if missing_fields:
            raise ValueError(
                f"Required field{'s' if len(missing_fields) > 1 else ''} "
                f"{', '.join(missing_fields)} not provided."
            )
        return self

    @field_validator("homepage_url")
    @classmethod
    def validate_homepage_url(cls, value: HttpUrl, info):
        # Check if context is provided
        env = info.context.get("env") if info.context else None
        if env == EnvironmentType.PRODUCTION and not str(value).startswith("https://"):
            raise ValueError(
                "homepage_url should start with https:// in production environment"
            )
        elif not (
            str(value).startswith("https://")
            or str(value).startswith("http://localhost")
            or str(value).startswith("http://127.0.0.1")
        ):
            raise ValueError(
                "homepage_url should start with https:// or http://localhost or http://127.0.0.1"
            )
        return value

    @classmethod
    def load(cls, file_path=default_manifest_file):
        if not os.path.exists(file_path):
            return cls()

        with open(file_path, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:
                return cls()

            if file_path.endswith((".yaml", ".yml")):
                return cls.model_validate(yaml.safe_load(data))
            elif file_path.endswith(".json"):
                return cls.model_validate_json(data)
            else:
                raise ValueError("Unsupported file format")

    def save(self, file_path=default_manifest_file):
        with open(file_path, "w", encoding="utf-8") as f:
            if file_path.endswith((".yaml", ".yml")):
                # Use model_dump to get a dictionary and then dump to YAML
                yaml.safe_dump(
                    self.model_dump(exclude_unset=True), f, default_flow_style=False
                )
            elif file_path.endswith(".json"):
                # Use model_dump_json for JSON serialization
                f.write(self.model_dump_json(exclude_unset=True, indent=4))
            else:
                raise ValueError("Unsupported file format")

    @classmethod
    def create_with_defaults(cls, file_path: str, user_data: dict = None):
        user_data = user_data or {}
        # Initialize with default values or user-provided values
        manifest = cls(
            app_name=user_data.get("app_name", "YourAppName"),
            app_desc=user_data.get("app_desc", "Short description of your app"),
            app_icon_url=user_data.get("app_icon_url", "https://example.com/icon.png"),
            homepage_url=user_data.get("homepage_url", "https://example.com"),
            app_key=user_data.get("app_key", "your-app-key"),
            app_desc_long=user_data.get(
                "app_desc_long", "A longer description of your app"
            ),
            creator_name=user_data.get("creator_name", "Your Name"),
            contact_email=user_data.get("contact_email", "your-email@example.com"),
            support_site_url=user_data.get(
                "support_site_url", "https://example.com/support"
            ),
            callback_urls=user_data.get(
                "callback_urls", ["https://example.com/callback"]
            ),
            screen_shots=user_data.get(
                "screen_shots",
                [
                    "https://example.com/screenshot_1.png",
                    "https://example.com/screenshot_2.png",
                    "https://example.com/screenshot_3.png",
                ],
            ),
            required_permissions=user_data.get(
                "required_permissions", ["resource:action"]
            ),
        )

        # Use the save method to write the manifest to a file
        manifest.save(file_path)
