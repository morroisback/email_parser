from email.message import Message
from .email_parsers import (
    AbstractEmailParser,
    InstagramVerificationEmailParser,
    DiscordVerificationEmailParser,
)


class EmailParserFactory:
    @staticmethod
    def get_parser(message: Message) -> AbstractEmailParser:
        subject = message.get("subject", "").lower()

        if "discord" in subject:
            return DiscordVerificationEmailParser()
        if "instagram" in subject:
            return InstagramVerificationEmailParser()

        raise ValueError("No suitable parser found for this email.")
