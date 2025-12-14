from dataclasses import dataclass


@dataclass
class EmailAccount:
    domain: str
    port: str
    address: str
    password: str
    is_oauth: bool = False
    refresh_token: str = ""
    client_id: str = ""
