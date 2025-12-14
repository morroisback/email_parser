from email.message import Message

from .email_parsers import (
    AbstractEmailParser,
    DiscordVerificationEmailParser,
    InstagramVerificationEmailParser,
)


class EmailParserFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmailParserFactory, cls).__new__(cls)
            cls._instance._parsers = {}
        return cls._instance

    def register_parser(self, keyword: str, parser_cls: AbstractEmailParser):
        self._parsers[keyword] = parser_cls

    def get_parser(self, message: Message) -> AbstractEmailParser:
        subject = message.get("subject", "").lower()

        for keyword, parser_cls in self._parsers.items():
            if keyword in subject:
                return parser_cls()

        raise ValueError("No suitable parser found for this email.")


parser_factory = EmailParserFactory()
parser_factory.register_parser("discord", DiscordVerificationEmailParser)
parser_factory.register_parser("instagram", InstagramVerificationEmailParser)
