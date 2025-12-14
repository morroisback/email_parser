import re

from dataclasses import dataclass

from email_parser import ImapClient, EmailAccount, EmailParserFactory
from email_parser import utils


@dataclass
class Proxy:
    host: str
    port: str
    username: str = ""
    password: str = ""
    refresh_url: str = ""

    def __str__(self) -> str:
        if self.username and self.password:
            return f"{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.host}:{self.port}"


def load_proxy_ports_file(proxies_file_path: str) -> list[Proxy]:
    with open(proxies_file_path, "r") as file:
        lines = list(map(lambda line: line.strip(), file.readlines()))

    proxies = []
    for proxy_line in lines:
        host = re.findall(r"@(.*?):", proxy_line)[0]
        port = re.findall(r"@.*?:(.*?):", proxy_line)[0]
        username = re.findall(r"http:\/\/(.*?):", proxy_line)[0]
        password = re.findall(r".*:(.*)@", proxy_line)[0]
        refresh_url = re.findall(r"\[(.*?)\]", proxy_line)[0]
        proxies.append(Proxy(host, port, username, password, refresh_url))
    return proxies


def load_oauth_emails(path: str, sep: str = ":") -> list[EmailAccount]:
    with open(path, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    emails = []
    for line in lines:
        parts = line.split(sep)
        emails.append(
            EmailAccount(
                domain="outlook.office365.com",
                port="993",
                address=parts[0],
                password=parts[1],
                is_oauth=True,
                refresh_token=parts[2],
                client_id=parts[3],
            )
        )
    return emails


def main() -> None:
    emails = load_oauth_emails(".env/oauth_emails.txt", "|")
    email_account = emails[4]

    proxies = load_proxy_ports_file(".env/proxy_ports.txt")
    proxy = proxies[0]

    try:
        with ImapClient(email_account, str(proxy)) as client:
            find = "discord"
            message = client.get_latest_message(sender=find)
            if message:
                print(f"{find} email found")
                utils.save_message(message, f".env/{find}_message.eml")
                utils.message_to_html(message, f".env/{find}.html")
                parser = EmailParserFactory.get_parser(message)
                print(parser.parse(message))
                return parser.parse(message)
            else:
                raise ValueError("No matching email found.")
    except ValueError as e:
        print(f"Parsing Error: {e}")
        return None


if __name__ == "__main__":
    main()
