from abc import ABC, abstractmethod
import imaplib
import requests

from .models import EmailAccount


class AuthStrategy(ABC):
    def __init__(self, email_account: EmailAccount, mail: imaplib.IMAP4_SSL) -> None:
        self.email_account = email_account
        self.mail = mail

    @abstractmethod
    def authenticate(self) -> None:
        pass


class SimpleAuthStrategy(AuthStrategy):
    def authenticate(self) -> None:
        status, _ = self.mail.login(self.email_account.address, self.email_account.password)
        if status != "OK":
            raise ConnectionError("Email login failed.")


class OAuthStrategy(AuthStrategy):
    def __init__(self, email_account: EmailAccount, mail: imaplib.IMAP4_SSL, proxy: str = None) -> None:
        super().__init__(email_account, mail)
        self.proxy = proxy
        self.access_token = self.get_oauth_token()

    def get_oauth_token(self) -> str:
        if not self.email_account.client_id or not self.email_account.refresh_token:
            raise ValueError("Client ID and refresh token are required for OAuth.")

        post_data = {
            "client_id": self.email_account.client_id,
            "refresh_token": self.email_account.refresh_token,
            "grant_type": "refresh_token",
        }

        proxies = {"http": f"http://{self.proxy}", "https": f"http://{self.proxy}"} if self.proxy else None

        try:
            response = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data=post_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                proxies=proxies,
            )
            response.raise_for_status()
            response_data = response.json()

            if "access_token" not in response_data:
                raise ConnectionError(f"Failed to get access token: {response.text}")

            if "refresh_token" in response_data:
                self.email_account.refresh_token = response_data["refresh_token"]

            return response_data["access_token"]
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error while requesting OAuth token: {e}")

    def authenticate(self) -> None:
        auth_string = f"user={self.email_account.address}\x01auth=Bearer {self.access_token}\x01\x01"
        status, _ = self.mail.authenticate("XOAUTH2", lambda x: auth_string.encode())
        if status != "OK":
            raise ConnectionError("Email authenticate failed.")
