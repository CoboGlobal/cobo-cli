import unittest

from cobo_cli.utils.signer import Signer


class TestSigner(unittest.TestCase):
    def setUp(self):
        self.signer = Signer(
            private_key="0281d349927d3b4342129aa4d86bd0ed70163feb7b8d06fecc25c667974b6297",
            public_key="f06a7074b7892a39139b6317509f9d0e01ae234cf17fc7bfa9db3d5957f931be",
            algorithm="ed25519",
        )

    def test_sign(self):
        signature = self.signer.sign("000000").hex()
        self.assertEqual(
            signature,
            "3f6b900e0b3d6d73baea6fb37ce564d47a51ffc3660facf1f421a5c05e3a9c15e281e197130647d5ad6a3192adf20ca9729ecd167181c07a74ae6ef958e0be09",  # noqa: E501
        )
