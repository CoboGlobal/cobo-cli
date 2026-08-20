"""Ed25519 signing helper for locally generated webhook test events.

Cobo signs webhook deliveries with an environment-specific key that is not
available locally, so `cobo webhook test` signs with a dedicated **test** key
whose private half is published here on purpose. Point your verifier at
TEST_PUBLIC_KEY while testing, then switch back to the environment key from
https://www.cobo.com/developers/v2/guides/webhooks-callbacks/set-up-endpoint
before going live.
"""

import hashlib
from typing import Dict, Tuple

from nacl.signing import SigningKey

# Fixed so that TEST_PUBLIC_KEY stays stable across runs and machines.
TEST_PRIVATE_KEY = "636f626f2d636c69206c6f63616c20776562686f6f6b2074657374206b657921"
TEST_PUBLIC_KEY = SigningKey(bytes.fromhex(TEST_PRIVATE_KEY)).verify_key.encode().hex()

# Cobo sends both spellings; a handler may read either one.
TIMESTAMP_HEADERS = ("BIZ_TIMESTAMP", "BIZ-TIMESTAMP")
SIGNATURE_HEADERS = ("BIZ_RESP_SIGNATURE", "BIZ-RESP-SIGNATURE")


def sign(raw_body: bytes, timestamp: str, private_key: str = TEST_PRIVATE_KEY) -> str:
    """Sign exactly the bytes that will be transmitted.

    The message is ``raw_body|timestamp`` hashed with double SHA-256, matching
    the verification steps documented for webhook endpoints. The caller must
    pass the same bytes it sends -- re-serialising the JSON afterwards changes
    key order and dropped fields, which invalidates the signature.
    """
    message = raw_body + b"|" + timestamp.encode()
    digest = hashlib.sha256(hashlib.sha256(message).digest()).digest()
    return SigningKey(bytes.fromhex(private_key)).sign(digest).signature.hex()


def build_headers(raw_body: bytes, timestamp: str) -> Tuple[Dict[str, str], str]:
    signature = sign(raw_body, timestamp)
    headers = {"Content-Type": "application/json"}
    for name in TIMESTAMP_HEADERS:
        headers[name] = timestamp
    for name in SIGNATURE_HEADERS:
        headers[name] = signature
    return headers, signature


# Cobo's own verification keys, as published in "Set up a callback or webhook
# endpoint" under Select Cobo's Public Key. A handler must be pointed at the
# one matching the environment it receives from; testing against one and
# deploying against the other passes every local check and then rejects every
# real delivery.
COBO_PUBLIC_KEYS = {
    "dev": "a04ea1d5fa8da71f1dcfccf972b9c4eba0a2d8aba1f6da26f49977b08a0d2718",
    "prod": "8d4a482641adb2a34b726f05827dba9a9653e5857469b8749052bf4458a86729",
}
