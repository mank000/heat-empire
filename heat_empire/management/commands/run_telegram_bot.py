from time import sleep

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections

from heat_empire.telegram_bot import TelegramAPI, TelegramBot, TelegramError
from heat_empire.telegram_credentials import load_credentials


class Command(BaseCommand):
    help = "Run one Telegram long-polling worker and deliver queued messages."

    def handle(self, *args, **options):
        if len(settings.SECRET_KEY) < 50 or settings.SECRET_KEY.startswith("django-insecure-"):
            raise CommandError("Set a strong DJANGO_SECRET_KEY before running the Telegram worker.")

        previous = None
        cursor = {}
        waiting = False
        while True:
            close_old_connections()
            try:
                credentials = load_credentials()
                if not credentials.ready:
                    if not waiting:
                        self.stdout.write("Waiting for Telegram bot settings.")
                        waiting = True
                    sleep(5)
                    continue
                if credentials != previous:
                    api = TelegramAPI(credentials.token)
                    bot = TelegramBot(api, credentials.pin, credentials.pin_is_hashed)
                    if previous is None or credentials.token != previous.token:
                        cursor = {}
                    previous = credentials
                    waiting = False
                    self.stdout.write("Telegram bot settings loaded.")
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
                    self.stderr.write("Telegram rejected polling. Check the token, webhook and other bot instances.")
                    sleep(15)
                    continue
                self.stderr.write(str(error))
                sleep(error.retry_after or 5)
            except OperationalError:
                self.stderr.write("Telegram worker could not access the database. Retrying.")
                sleep(2)
            except InvalidToken:
                self.stderr.write("Unable to decrypt Telegram token. Check DJANGO_SECRET_KEY.")
                sleep(15)
