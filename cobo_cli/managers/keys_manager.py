import secrets

from nacl.signing import SigningKey


class KeysManager:
    @classmethod
    def generate(cls, alg, secret=None):
        if not secret:
            secret = secrets.token_hex(32)

        if alg == "ed25519":
            sk = SigningKey(bytes.fromhex(secret))
            return secret, sk.verify_key.encode().hex()

        raise NotImplementedError("Algorithm {} is not supported".format(alg))
