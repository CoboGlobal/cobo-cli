import os

from django.conf import settings

# Log

LOGGING = settings.LOGGING

LOGGING["loggers"] = {}
LOGGING["handlers"] = {"null": {"level": "DEBUG", "class": "logging.NullHandler"}}
LOGGING["root"] = {"level": "ERROR", "handlers": ["console"]}
LOGGING["loggers"]["django"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
    "formatter": "verbose",
}

LOGGING["handlers"]["console"] = {
    "level": "DEBUG",
    "class": "logging.StreamHandler",
    "formatter": "verbose",
}

LOGGING["loggers"]["django.celery"] = {"level": "DEBUG", "handlers": ["console"]}
LOGGING["loggers"]["celery"] = {"level": "DEBUG", "handlers": ["console"]}

COMMON_LOG_FILE = "/dev/null"
CELERY_LOG_FILE = "/dev/null"
SYNC_SERVICE_LOG_FILE = "/dev/null"
SIGNER_LOG_FILE = "/dev/null"
TXDB_LOG_FILE = "/dev/null"

ENABLE_SQL_LOGGING = os.getenv("SQL_LOGGING", False)
if ENABLE_SQL_LOGGING in ("1", "True", "true", "Y", "y"):
    ENABLE_SQL_LOGGING = True
elif ENABLE_SQL_LOGGING in ("0", "False", "false", "N", "n"):
    ENABLE_SQL_LOGGING = False
else:
    ENABLE_SQL_LOGGING = False

if not ENABLE_SQL_LOGGING:
    LOGGING["loggers"]["django.db.backends"] = {
        "handlers": ["null"],
        "propagate": False,
        "level": "DEBUG",
    }
