import json
import logging
from datetime import datetime
from urllib.parse import urlencode

import requests

from cobo_cli.utils.signer import Signer

logger = logging.getLogger(__name__)


class OrgTokenManager(object):
    @classmethod
    def get_token(cls, api_host, client_id, app_key, app_secret, org_uuid) -> dict:
        logger.debug(
            f"OrgTokenManager get_token called with client_id={client_id}, "
            f"app_key={app_key}, app_secret={app_secret}, org_uuid={org_uuid}"
        )

        params = {
            "client_id": client_id,
            "org_id": org_uuid,
            "grant_type": "org_implicit",
        }
        api_path = "/v2/oauth/token"

        now = datetime.now()
        api_nonce = str(int(now.timestamp() * 1000))

        content = "|".join(
            (
                "GET",
                api_path,
                api_nonce,
                urlencode(params),
                "",
            )
        )
        api_sign = (
            Signer(
                private_key=app_secret,
                public_key=app_key,
            )
            .sign(content)
            .hex()
        )

        headers = {
            "BIZ-API-KEY": app_key,
            "BIZ-API-NONCE": api_nonce,
            "BIZ-API-SIGNATURE": api_sign,
        }
        logger.debug(
            f"OrgTokenManager get_token, api_host: {api_host}, content: {content}, "
            f"api_sign: {api_sign}"
        )

        # 发送 GET 请求
        response = requests.get(f"{api_host}{api_path}", params=params, headers=headers)
        logger.debug(f"OrgTokenManager get_token, response: {response.text}")
        return response.json()

    @classmethod
    def refresh_token(
        cls, api_host, client_id, app_key, app_secret, org_uuid, refresh_token
    ) -> dict:
        logger.debug(
            f"OrgTokenManager refresh_token called with client_id={client_id}, "
            f"app_key={app_key}, app_secret={app_secret}, org_uuid={org_uuid}, refresh_token={refresh_token}"
        )

        params = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        api_path = "/v2/oauth/token"

        now = datetime.now()
        api_nonce = str(int(now.timestamp() * 1000))

        content = "|".join(
            (
                "POST",
                api_path,
                api_nonce,
                urlencode({}),
                json.dumps(params, allow_nan=False),
            )
        )

        api_sign = (
            Signer(
                private_key=app_secret,
                public_key=app_key,
            )
            .sign(content)
            .hex()
        )

        headers = {
            "BIZ-API-KEY": app_key,
            "BIZ-API-NONCE": api_nonce,
            "BIZ-API-SIGNATURE": api_sign,
        }

        # 发送 POST 请求
        response = requests.post(f"{api_host}{api_path}", json=params, headers=headers)
        return response.json()
