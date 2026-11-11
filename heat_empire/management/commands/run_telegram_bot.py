import os
import re
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections

from heat_empire.telegram_bot import TelegramAPI, TelegramBot, TelegramError


class Command(BaseCommand):
    help = "Run one Telegram long-polling worker and deliver queued messages."

    def handle(self, *args, **options):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        pin = os.environ.get("TELEGRAM_ACCESS_PIN", "")
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
            raise CommandError("Set TELEGRAM_BOT_TOKEN to the token from BotFather.")
        if not re.fullmatch(r"[0-9]{8,32}", pin):
            raise CommandError("Set TELEGRAM_ACCESS_PIN to a random PIN with 8–32 digits.")

        if len(settings.SECRET_KEY) < 50:
            raise CommandError("Set a strong DJANGO_SECRET_KEY before running the Telegram worker.")

        api = TelegramAPI(token)
        bot = TelegramBot(api, pin)
        cursor = {}
        self.stdout.write("Telegram worker started.")
        while True:
            close_old_connections()
            try:
                wait = bot.flush()
                if wait:
                    sleep(wait)
                    continue
                updates = api.call("getUpdates", timeout=5, limit=1, allowed_updates=["message"], **cursor)
                for update in updates:
                    bot.handle_update(update)
                    cursor["offset"] = update["update_id"] + 1
            except TelegramError as error:
                if error.code in (401, 409):
                    raise CommandError("Telegram rejected polling. Check the token, webhook and other bot instances.") from None
                self.stderr.write(str(error))
                sleep(error.retry_after or 5)
            except OperationalError:
                self.stderr.write("Telegram worker could not access the database. Retrying.")
                sleep(2)
