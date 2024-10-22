from dataclasses import dataclass
from cobo_cli.managers import ConfigManager
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.auth_methods import AuthMethodType

@dataclass
class CommandContext:
    env: EnvironmentType
    auth_method: AuthMethodType
    config_manager: ConfigManager
    api_spec: dict = None
