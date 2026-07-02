from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Start the Telegram bot in polling mode"

    def handle(self, *args, **options) -> None:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN is not set. "
                "Add it to your .env file before starting the bot."
            )

        from apps.bot.bot import build_app

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (polling mode)..."))
        app = build_app(token)
        app.run_polling(allowed_updates=["message", "callback_query"])
