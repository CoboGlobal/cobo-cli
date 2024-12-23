from abc import ABCMeta, abstractmethod


class ApiSigner(metaclass=ABCMeta):
    @abstractmethod
    def get_headers(self):
        raise NotImplementedError


class UserTokenSigner(ApiSigner):
    def __init__(self, user_token):
        self.user_token = user_token

    def get_headers(self):
        return {
            "AUTHORIZATION": f"Bearer {self.user_token}",
        }
