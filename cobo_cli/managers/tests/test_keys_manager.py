import unittest

from cobo_cli.managers import KeysManager


class TestKeysManager(unittest.TestCase):
    def test_generation(self):
        secret = "0281d349927d3b4342129aa4d86bd0ed70163feb7b8d06fecc25c667974b6297"
        _, pubkey = KeysManager.generate(alg="ed25519", secret=secret)
        self.assertEqual(
            pubkey, "f06a7074b7892a39139b6317509f9d0e01ae234cf17fc7bfa9db3d5957f931be"
        )
