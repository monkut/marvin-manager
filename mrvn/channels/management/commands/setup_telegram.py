import getpass
import logging
from typing import TYPE_CHECKING

import httpx
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.management.base import BaseCommand, CommandError

from channels.models import Channel, ChannelCredential, ChannelType

if TYPE_CHECKING:
    from argparse import ArgumentParser

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Set up a Telegram bot channel integration"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--name", type=str, help="Name for this Telegram channel (default: Telegram)")
        parser.add_argument("--bot-token", type=str, help="Telegram Bot Token from @BotFather")
        parser.add_argument("--owner", type=str, help="Username of the channel owner")
        parser.add_argument("--webhook-url", type=str, help="Webhook URL for receiving updates (optional)")
        parser.add_argument("--non-interactive", action="store_true", help="Run without prompts")

    def handle(self, *args, **options) -> None:
        self.non_interactive = options["non_interactive"]
        self.stdout.write(self.style.SUCCESS("\n=== Telegram Bot Setup ===\n"))

        name = self._get_channel_name(options)
        owner = self._get_owner(options)
        bot_token = self._get_bot_token(options)
        webhook_url = self._get_webhook_url(options)

        self._validate_and_create(name, owner, bot_token, webhook_url)

    def _get_channel_name(self, options: dict) -> str:
        name = options["name"] or (
            "Telegram" if self.non_interactive else self._prompt("Channel name", default="Telegram")
        )
        if Channel.objects.filter(name=name, channel_type=ChannelType.TELEGRAM).exists():
            raise CommandError(f"A Telegram channel named '{name}' already exists.")
        return name

    def _get_owner(self, options: dict) -> AbstractUser:
        owner_username = options["owner"]
        if not owner_username:
            if self.non_interactive:
                raise CommandError("--owner is required in non-interactive mode")
            owner_username = self._prompt("Owner username")

        try:
            return User.objects.get(username=owner_username)
        except User.DoesNotExist as err:
            raise CommandError(f"User '{owner_username}' not found.") from err

    def _get_bot_token(self, options: dict) -> str:
        bot_token = options["bot_token"]
        if not bot_token:
            if self.non_interactive:
                raise CommandError("--bot-token is required in non-interactive mode")
            self.stdout.write("\nTelegram Bot Token")
            self.stdout.write("Get it from @BotFather: https://t.me/BotFather")
            self.stdout.write("  1. Send /newbot to create a new bot")
            self.stdout.write("  2. Follow the prompts to set name and username")
            self.stdout.write("  3. Copy the token provided")
            bot_token = self._prompt_secret("Bot Token")

        if ":" not in bot_token:
            self.stdout.write(self.style.WARNING("Warning: Token format looks incorrect (should contain ':')"))
        return bot_token

    def _get_webhook_url(self, options: dict) -> str:
        webhook_url = options["webhook_url"] or ""
        if not webhook_url and not self.non_interactive:
            self.stdout.write("\nWebhook URL (optional)")
            self.stdout.write("Leave empty to use polling mode (simpler, good for development)")
            self.stdout.write("Set a URL for webhook mode (better for production)")
            webhook_url = self._prompt("Webhook URL (press Enter to skip)", required=False)
        return webhook_url

    def _validate_and_create(self, name: str, owner: AbstractUser, bot_token: str, webhook_url: str) -> None:
        self.stdout.write("\nValidating bot token...")
        bot_info = self._validate_telegram_token(bot_token)
        if not bot_info:
            if self.non_interactive:
                raise CommandError("Failed to validate Telegram bot token")
            if not self._confirm("Validation failed. Continue anyway?"):
                raise CommandError("Setup cancelled.")
            bot_info = {}

        self.stdout.write("\nCreating channel...")
        channel = Channel.objects.create(
            name=name,
            channel_type=ChannelType.TELEGRAM,
            owner=owner,
            is_active=True,
            config={
                "webhook_url": webhook_url,
                "use_polling": not bool(webhook_url),
                "bot_username": bot_info.get("username", ""),
            },
        )

        ChannelCredential.objects.create(
            channel=channel,
            encrypted_data={"bot_token": bot_token},
        )

        self._print_success(channel, owner, webhook_url, bot_info)

    def _print_success(self, channel: Channel, owner: AbstractUser, webhook_url: str, bot_info: dict) -> None:
        self.stdout.write(self.style.SUCCESS(f"\nTelegram channel '{channel.name}' created successfully!"))
        self.stdout.write(f"  ID: {channel.id}")
        self.stdout.write(f"  Owner: {owner.username}")
        if bot_info:
            self.stdout.write(f"  Bot: @{bot_info.get('username', 'unknown')}")
        self.stdout.write(f"  Mode: {'Webhook' if webhook_url else 'Polling'}")

        self.stdout.write("\nNext steps:")
        if webhook_url:
            self.stdout.write(f"  1. Ensure {webhook_url} is publicly accessible")
            self.stdout.write("  2. The webhook will be registered when the bot starts")
        else:
            self.stdout.write("  1. Start the bot daemon to begin receiving messages")
        self.stdout.write("  2. Send /start to your bot to test the connection")

        if bot_info.get("username"):
            self.stdout.write(f"\nBot link: https://t.me/{bot_info['username']}")

    def _prompt(self, label: str, default: str | None = None, required: bool = True) -> str:
        prompt_text = f"{label} [{default}]: " if default else f"{label}: "
        self.stdout.write(prompt_text, ending="")
        value = input().strip()
        if not value and default:
            return default
        if not value and required:
            raise CommandError(f"{label} is required.")
        return value

    def _prompt_secret(self, label: str, required: bool = True) -> str:
        try:
            value = getpass.getpass(f"{label}: ")
        except EOFError:
            if required:
                raise CommandError(f"{label} is required.") from None
            return ""
        if not value and required:
            raise CommandError(f"{label} is required.")
        return value

    def _confirm(self, message: str) -> bool:
        self.stdout.write(f"{message} [y/N]: ", ending="")
        return input().strip().lower() in ("y", "yes")

    def _validate_telegram_token(self, bot_token: str) -> dict | None:
        try:
            response = httpx.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10.0)
            data = response.json()

            if data.get("ok"):
                result = data["result"]
                self.stdout.write(self.style.SUCCESS(f"  Bot name: {result.get('first_name', 'Unknown')}"))
                self.stdout.write(self.style.SUCCESS(f"  Username: @{result.get('username', 'unknown')}"))
                self.stdout.write(self.style.SUCCESS(f"  Bot ID: {result.get('id', 'unknown')}"))
                return result

            self.stdout.write(self.style.ERROR(f"  Error: {data.get('description', 'Unknown error')}"))
        except httpx.RequestError as e:
            self.stdout.write(self.style.ERROR(f"  Network error: {e}"))
        return None
