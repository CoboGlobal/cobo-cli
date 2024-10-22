from enum import Enum


class EnvironmentType(Enum):
    SANDBOX = "sandbox"
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"

    @classmethod
    def values(cls):
        return [e.value for e in cls]


EnvironmentType.SANDBOX.default_app_id = "b70c5912-a039-4a92-bba7-a1b26512275a"
EnvironmentType.DEVELOPMENT.default_app_id = "98bbd74a-49b1-40ef-a7f4-207b2c708bd7"
EnvironmentType.PRODUCTION.default_app_id = ""
