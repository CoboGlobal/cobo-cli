import os

TEST_TYPES = ("inttest", "unittest")

test_type = os.getenv("TEST_TYPE", "unittest")
if test_type not in TEST_TYPES:
    test_type = "unittest"

settings_name = test_type + "_settings"
if settings_name == "unittest_settings":
    try:
        from tests.testenv.unittest_settings import *  # noqa
    except ImportError:
        pass
