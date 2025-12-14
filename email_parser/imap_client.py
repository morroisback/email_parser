import imaplib
import email
import re

from datetime import datetime, timezone
from email.message import Message
from email.header import decode_header, make_header

from .models import EmailAccount
from .auth import AuthStrategy, SimpleAuthStrategy, OAuthStrategy


class ImapClient:
    def __init__(self, email_account: EmailAccount, proxy: str | None = None) -> None:
        self.email_account = email_account
        self.proxy = proxy
        self.mail: imaplib.IMAP4_SSL | None = None
        self.is_logged_in = False

    def __enter__(self) -> "ImapClient":
        try:
            self.mail = imaplib.IMAP4_SSL(self.email_account.domain, int(self.email_account.port))
            auth_strategy = self.get_auth_strategy()
            auth_strategy.authenticate()

            self.is_logged_in = True
            return self
        except Exception as e:
            raise ConnectionError(f"Failed to connect to IMAP server: {e}")

    def get_auth_strategy(self) -> AuthStrategy:
        if self.email_account.is_oauth:
            return OAuthStrategy(self.email_account, self.mail, self.proxy)
        else:
            return SimpleAuthStrategy(self.email_account, self.mail)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_logged_in and self.mail:
            self.mail.logout()
            self.is_logged_in = False

    def check_message_criteria(
        self,
        message: Message,
        sender: str | None,
        subject: str | None,
        within_seconds: int | None,
    ) -> bool:
        if sender:
            from_header = str(make_header(decode_header(message["From"])))
            if sender.lower() not in from_header.lower():
                return False

        if subject:
            subject_header = str(make_header(decode_header(message["Subject"])))
            if subject.lower() not in subject_header.lower():
                return False

        if within_seconds:
            date_header = str(make_header(decode_header(message["Date"])))
            date_header = re.sub(r'\s*\([^)]*\)', '', date_header)
            message_dt = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %z").astimezone(timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if (now_utc - message_dt).total_seconds() > within_seconds:
                return False

        return True

    def search_messages(
        self,
        sender: str = None,
        subject: str = None,
        folder: str = "inbox",
        within_seconds: int | None = None,
    ) -> list[Message]:
        if not self.is_logged_in or not self.mail:
            raise RuntimeError("Not logged in.")

        status, _ = self.mail.select(f'"{folder}"')
        if status != "OK":
            raise ValueError(f"Folder '{folder}' not found.")

        status, mail_ids_raw = self.mail.search(None, "ALL")
        if status != "OK" or not mail_ids_raw[0]:
            return []

        matching_messages = []
        mail_ids = mail_ids_raw[0].split()

        for mail_id in reversed(mail_ids):
            status, raw_mail = self.mail.fetch(mail_id, "(RFC822)")
            if status == "OK":
                message = email.message_from_bytes(raw_mail[0][1])
                if self.check_message_criteria(message, sender, subject, within_seconds):
                    matching_messages.append(message)

        return matching_messages

    def get_latest_message(
        self,
        sender: str = None,
        subject: str = None,
        folders: list[str] | None = None,
        within_seconds: int | None = None,
    ) -> Message | None:
        if folders is None:
            folders = ["inbox", "junk"]

        for folder in folders:
            try:
                messages = self.search_messages(sender, subject, folder=folder, within_seconds=within_seconds)
                if messages:
                    return messages[0]
            except ValueError:
                continue
        return None

    def delete_messages(
        self,
        sender: str = None,
        subject: str = None,
        folder: str = "inbox",
        within_seconds: int | None = None,
    ) -> None:
        if not self.is_logged_in or not self.mail:
            raise RuntimeError("Not logged in.")

        status, _ = self.mail.select(f'"{folder}"')
        if status != "OK":
            raise ValueError(f"Folder '{folder}' not found.")

        status, mail_ids_raw = self.mail.search(None, "ALL")
        if status != "OK" or not mail_ids_raw[0]:
            return

        ids_to_delete = []
        mail_ids = mail_ids_raw[0].split()

        for mail_id in mail_ids:
            status, raw_mail = self.mail.fetch(mail_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status == "OK":
                message = email.message_from_bytes(raw_mail[0][1])
                if self.check_message_criteria(message, sender, subject, within_seconds):
                    ids_to_delete.append(mail_id)

        if ids_to_delete:
            for mail_id in ids_to_delete:
                self.mail.store(mail_id, "+FLAGS", "\\Deleted")
            self.mail.expunge()

    def delete_all_messages(self, folder: str = "inbox") -> None:
        if not self.is_logged_in or not self.mail:
            raise RuntimeError("Not logged in.")

        status, _ = self.mail.select(f'"{folder}"')
        if status != "OK":
            raise ValueError(f"Folder '{folder}' not found.")

        status, mail_ids_raw = self.mail.search(None, "ALL")
        if status == "OK" and mail_ids_raw[0]:
            mail_ids = mail_ids_raw[0].split()
            for mail_id in mail_ids:
                self.mail.store(mail_id, "+FLAGS", "\\Deleted")
            self.mail.expunge()
