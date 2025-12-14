import email
import pickle

from email.message import Message
from pathlib import Path


def save_message(message: Message, file_path: str | None = None) -> str:
    if file_path is None:
        subject = message.get("Subject", "message")
        file_path = f"email_{subject[:30]}.eml"

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if str(file_path).endswith(".pkl"):
        with open(file_path, "wb") as f:
            pickle.dump(message, f)
    else:
        with open(file_path, "wb") as f:
            f.write(message.as_bytes())

    return str(file_path)


def load_message(file_path: str) -> Message:
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Файл {file_path} не найден.")

    if str(file_path).endswith(".pkl"):
        with open(file_path, "rb") as f:
            return pickle.load(f)
    else:
        with open(file_path, "rb") as f:
            return email.message_from_bytes(f.read())


def message_to_html(message: Message, file_path: str | None = None) -> str:
    if file_path is None:
        subject = message.get("Subject", "message")
        file_path = f"email_{subject[:30]}.html"

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = None

    if message.is_multipart():
        for payload in message.get_payload():
            if payload.get_content_type() == "text/html":
                html_content = payload.get_payload(decode=True).decode("utf-8")
                break
    else:
        if message.get_content_type() == "text/html":
            html_content = message.get_payload(decode=True).decode("utf-8")

    if html_content is None:
        raise ValueError("No HTML content found in email.")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(file_path)
