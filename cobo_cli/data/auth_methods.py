from enum import Enum

class AuthMethodType(Enum):
    APIKEY = "apikey"
    USER = "user"
    ORG = "org"

    @classmethod
    def values(cls):
        return [e.value for e in cls]