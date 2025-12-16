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


available_wallet_types = [
    "Custodial",
    "MPC",
    "SmartContract",
    "Exchange",
    "User-Controlled",
    "Org-Controlled",
    "Asset",
    "Web3",
    "Safe{Wallet}",
    "Main",
]


# Define the tuple separately
class Manifest(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=30)
    app_id: Optional[str] = ""
    dev_app_id: Optional[str] = ""
    client_id: Optional[str] = ""
    dev_client_id: Optional[str] = ""
    callback_urls: List[HttpUrl] = Field(default_factory=list)
    app_desc: str = Field(..., max_length=200)
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
    wallet_types: List[str] = Field(default_factory=list)
    is_policy_reminded: Optional[bool] = True
    required_permissions: List[str] = Field(default_factory=list)
    optional_permissions: List[str] = Field(default_factory=list)
    framework: Optional[FrameworkEnum] = None
    allow_multiple_tokens: Optional[bool] = False
    grant_dimension: Optional[GrantDimensionEnum] = GrantDimensionEnum.ORG
    operation_approval_rules: List[dict] = Field(default_factory=list)
    app_roles: List[dict] = Field(default_factory=list)

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

    @field_validator("wallet_types")
    @classmethod
    def validate_wallet_types(cls, wallet_types: List[str]):
        _invalid_wallet_type = [
            item for item in wallet_types if item.strip() not in available_wallet_types
        ]
        if len(_invalid_wallet_type) > 0:
            raise ValueError(
                (
                    f"We don't support {_invalid_wallet_type} for now, "
                    f"supported wallet types are {available_wallet_types}."
                )
            )
        return wallet_types

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
    def load(cls, file_path=None) -> tuple["Manifest" or None, str or None]:
        manifest_path = None
        if file_path:
            manifest_path = manifest_path
        else:
            possible_manifest_location = [
                f"../{default_manifest_file}",
                f"./{default_manifest_file}",
            ]
            for _path in possible_manifest_location:
                if os.path.isfile(_path):
                    manifest_path = _path
        if manifest_path:
            manifest_path = os.path.abspath(manifest_path)
        if not manifest_path or not os.path.isfile(manifest_path):
            return None, None
        return cls._load(manifest_path), manifest_path

    @classmethod
    def _load(cls, file_path=default_manifest_file):
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
            homepage_url=user_data.get("homepage_url", "http://localhost:5000"),
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
            wallet_types=user_data.get("wallet_types", []),
            is_policy_reminded=user_data.get("is_policy_reminded", True),
            allow_multiple_tokens=user_data.get("allow_multiple_tokens", False),
            grant_dimension=user_data.get(
                "grant_dimension", GrantDimensionEnum.ORG.value
            ),
            required_permissions=user_data.get(
                "required_permissions", ["resource:action"]
            ),
            operation_approval_rules=user_data.get("operation_approval_rules", []),
        )

        # Use the save method to write the manifest to a file
        manifest.save(file_path)
