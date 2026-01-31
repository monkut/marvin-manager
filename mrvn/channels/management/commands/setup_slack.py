import getpass
import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.management.base import BaseCommand, CommandError

from channels.models import Channel, ChannelCredential, ChannelType

if TYPE_CHECKING:
    from argparse import ArgumentParser

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Set up a Slack channel integration"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--name", type=str, help="Name for this Slack channel (default: Slack)")
        parser.add_argument("--bot-token", type=str, help="Slack Bot Token (xoxb-...)")
        parser.add_argument("--signing-secret", type=str, help="Slack Signing Secret")
        parser.add_argument("--app-token", type=str, help="Slack App Token for Socket Mode (xapp-..., optional)")
        parser.add_argument("--owner", type=str, help="Username of the channel owner")
        parser.add_argument("--non-interactive", action="store_true", help="Run without prompts")

    def handle(self, *args, **options) -> None:
        self.non_interactive = options["non_interactive"]
        self.stdout.write(self.style.SUCCESS("\n=== Slack Channel Setup ===\n"))

        name = self._get_channel_name(options)
        owner = self._get_owner(options)
        bot_token = self._get_bot_token(options)
        signing_secret = self._get_signing_secret(options)
        app_token = self._get_app_token(options)

        self._validate_and_create(name, owner, bot_token, signing_secret, app_token)

    def _get_channel_name(self, options: dict) -> str:
        name = options["name"] or ("Slack" if self.non_interactive else self._prompt("Channel name", default="Slack"))
        if Channel.objects.filter(name=name, channel_type=ChannelType.SLACK).exists():
            raise CommandError(f"A Slack channel named '{name}' already exists.")
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
            self.stdout.write("\nSlack Bot Token (starts with xoxb-)")
            self.stdout.write("Get it from: https://api.slack.com/apps -> OAuth & Permissions")
            bot_token = self._prompt_secret("Bot Token")

        if not bot_token.startswith("xoxb-"):
            self.stdout.write(self.style.WARNING("Warning: Bot token should start with 'xoxb-'"))
        return bot_token

    def _get_signing_secret(self, options: dict) -> str:
        signing_secret = options["signing_secret"]
        if not signing_secret:
            if self.non_interactive:
                raise CommandError("--signing-secret is required in non-interactive mode")
            self.stdout.write("\nSlack Signing Secret")
            self.stdout.write("Get it from: https://api.slack.com/apps -> Basic Information")
            signing_secret = self._prompt_secret("Signing Secret")
        return signing_secret

    def _get_app_token(self, options: dict) -> str:
        app_token = options["app_token"] or ""
        if not app_token and not self.non_interactive:
            self.stdout.write("\nSlack App Token for Socket Mode (optional, starts with xapp-)")
            self.stdout.write("Get it from: https://api.slack.com/apps -> Basic Information -> App-Level Tokens")
            app_token = self._prompt_secret("App Token (press Enter to skip)", required=False)

        if app_token and not app_token.startswith("xapp-"):
            self.stdout.write(self.style.WARNING("Warning: App token should start with 'xapp-'"))
        return app_token

    def _validate_and_create(
        self, name: str, owner: AbstractUser, bot_token: str, signing_secret: str, app_token: str
    ) -> None:
        self.stdout.write("\nValidating credentials...")
        if not self._validate_slack_credentials(bot_token):
            if self.non_interactive:
                raise CommandError("Failed to validate Slack credentials")
            if not self._confirm("Validation failed. Continue anyway?"):
                raise CommandError("Setup cancelled.")

        self.stdout.write("\nCreating channel...")
        channel = Channel.objects.create(
            name=name,
            channel_type=ChannelType.SLACK,
            owner=owner,
            is_active=True,
            config={"socket_mode": bool(app_token)},
        )

        credential_data = {"bot_token": bot_token, "signing_secret": signing_secret}
        if app_token:
            credential_data["app_token"] = app_token

        ChannelCredential.objects.create(channel=channel, encrypted_data=credential_data)

        self._print_success(channel, owner, app_token)

    def _print_success(self, channel: Channel, owner: AbstractUser, app_token: str) -> None:
        self.stdout.write(self.style.SUCCESS(f"\nSlack channel '{channel.name}' created successfully!"))
        self.stdout.write(f"  ID: {channel.id}")
        self.stdout.write(f"  Owner: {owner.username}")
        self.stdout.write(f"  Socket Mode: {'Enabled' if app_token else 'Disabled'}")
        self.stdout.write("\nNext steps:")
        self.stdout.write("  1. Configure Event Subscriptions in your Slack App")
        self.stdout.write("  2. Add bot scopes: chat:write, app_mentions:read, im:history, im:read")
        self.stdout.write("  3. Install the app to your workspace")
        if not app_token:
            self.stdout.write("  4. Set up a webhook endpoint for events")

    def _prompt(self, label: str, default: str | None = None) -> str:
        prompt_text = f"{label} [{default}]: " if default else f"{label}: "
        self.stdout.write(prompt_text, ending="")
        value = input().strip()
        if not value and default:
            return default
        if not value:
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

    def _validate_slack_credentials(self, bot_token: str) -> bool:
        try:
            from slack_sdk import WebClient  # noqa: PLC0415
            from slack_sdk.errors import SlackApiError  # noqa: PLC0415
        except ImportError:
            self.stdout.write(self.style.WARNING("  slack-sdk not available, skipping validation"))
            return True

        try:
            client = WebClient(token=bot_token)
            response = client.auth_test()

            if response["ok"]:
                self.stdout.write(self.style.SUCCESS(f"  Connected as: {response['user']}"))
                self.stdout.write(self.style.SUCCESS(f"  Workspace: {response['team']}"))
                return True

            self.stdout.write(self.style.ERROR(f"  Error: {response.get('error', 'Unknown error')}"))
        except SlackApiError as e:
            self.stdout.write(self.style.ERROR(f"  Slack API Error: {e.response['error']}"))
        return False
