import logging
import uuid

import requests

logger = logging.getLogger(__name__)


class UserTokenManager(object):
    @classmethod
    def init_auth(cls, api_host):
        client_id = "cobo_cli"
        logger.debug(
            f"UserTokenManager init_auth called with client_id={client_id}, "
            f"api_host={api_host}"
        )

        params = {
            "client_id": client_id,
            "response_type": "code",
            "state": str(uuid.uuid4()),
        }
        api_path = "/v2/oauth/authorize/initiate_auth"

        response = requests.post(f"{api_host}{api_path}", json=params, timeout=10)
        return response.json()

    @classmethod
    def get_user_token(cls, token_url: str):
        logger.debug(
            f"UserTokenManager get_user_token called with token_url={token_url}"
        )

        response = requests.get(token_url, params={}, timeout=10)
        logger.debug(f"UserTokenManager get_user_token, response: {response.text}")
        return response.json()
