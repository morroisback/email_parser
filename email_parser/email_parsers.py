import re

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from email.message import Message


class AbstractEmailParser(ABC):
    def get_html_body(self, message: Message) -> str:
        if message.is_multipart():
            for payload in message.get_payload():
                if payload.get_content_type() == "text/html":
                    return payload.get_payload(decode=True).decode("utf-8")
        else:
            if message.get_content_type() == "text/html":
                return message.get_payload(decode=True).decode("utf-8")
        raise ValueError("No HTML content found in email.")

    @abstractmethod
    def parse(self, message: Message) -> str:
        raise NotImplementedError


class DiscordVerificationEmailParser(AbstractEmailParser):
    def parse(self, message: Message) -> str:
        body = self.get_html_body(message)
        url_match = re.search(r'<a\s+href="([^"]*?)".*?>\s*Verify Email\s*<\/a>', body)
        if url_match:
            return url_match.group(1)

        raise ValueError("Discord verification link not found in email.")


class InstagramVerificationEmailParser(AbstractEmailParser):
    def parse(self, message: Message) -> str:
        body = self.get_html_body(message)
        soup = BeautifulSoup(body, "lxml")
        code_element = soup.find("td", style=lambda x: x and "font-size:32px" in x)
        if code_element:
            code = code_element.get_text(strip=True)
            if code and code.isdigit():
                return code

        raise ValueError("Instagram verification code not found.")
