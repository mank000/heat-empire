import os
import re
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field

from cryptography.fernet import Fernet
from django.utils.crypto import salted_hmac

from .models import TelegramBotSettings


TOKEN_PATTERN = r"[0-9]+:[A-Za-z0-9_-]+"
PIN_PATTERN = r"[0-9]{8,32}"


@dataclass(frozen=True)
class BotCredentials:
    token: str = field(repr=False)
    pin: str = field(repr=False)
    pin_is_hashed: bool = False

    @property
    def ready(self):
        return bool(re.fullmatch(TOKEN_PATTERN, self.token) and (
            self.pin if self.pin_is_hashed else re.fullmatch(PIN_PATTERN, self.pin)
        ))


def token_cipher():
    key = salted_hmac("heat-empire-telegram-token", "", algorithm="sha256").digest()
    return Fernet(urlsafe_b64encode(key))


def load_credentials():
    stored = TelegramBotSettings.objects.get(pk=1)
    token = token_cipher().decrypt(stored.encrypted_token.encode()).decode() if stored.encrypted_token else ""
    return BotCredentials(
        token=token or os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        pin=stored.pin_hash or os.environ.get("TELEGRAM_ACCESS_PIN", ""),
        pin_is_hashed=bool(stored.pin_hash),
    )
