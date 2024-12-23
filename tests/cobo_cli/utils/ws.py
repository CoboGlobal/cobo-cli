import hashlib
import time

from nacl.signing import SigningKey


def generate_ws_apikey_auth_headers(
    api_secret: str,
    path,
):
    timestamp = str(int(time.time() * 1000))
    digest = hashlib.sha256(
        hashlib.sha256(f"{path}|{timestamp}".encode()).digest()
    ).digest()
    sk = SigningKey(bytes.fromhex(api_secret))
    signature = sk.sign(digest).signature
    vk = bytes(sk.verify_key)
    headers = {
        "Biz-Api-Key": vk.hex(),
        "Biz-Api-Nonce": timestamp,
        "Biz-Api-Signature": signature.hex(),
    }
    return headers
