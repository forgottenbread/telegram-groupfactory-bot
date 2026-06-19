import os
from dataclasses import dataclass
from typing import Set


def _parse_chat_ids(value: str) -> Set[int]:
    chat_ids = set()
    for item in (value or "").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        chat_ids.add(int(item))
    return chat_ids


@dataclass(frozen=True)
class Config:
    bot_token: str
    api_base_url: str
    api_key: str
    allowed_chat_ids: Set[int]
    request_timeout: float


def load_config() -> Config:
    allowed_chat_ids = _parse_chat_ids(
        os.environ.get("BOT_ALLOWED_CHAT_IDS") or os.environ.get("STAFF_CHAT_ID", "")
    )

    return Config(
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        api_base_url=os.environ.get("GROUPFACTORY_API_BASE_URL", "http://groupfactory:8000").rstrip("/"),
        api_key=os.environ["GROUPFACTORY_API_KEY"],
        allowed_chat_ids=allowed_chat_ids,
        request_timeout=float(os.environ.get("GROUPFACTORY_API_TIMEOUT", "300")),
    )
