import logging
import signal
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

from django.core.management.base import BaseCommand, CommandError

from channels.models import Channel, ChannelType

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from types import FrameType

    from slack_bolt import App

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Slack bot daemon for processing messages"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--channel-id",
            type=int,
            help="Specific channel ID to run (default: run first active Slack channel)",
        )

    def handle(self, *args, **options) -> None:
        channel_id = options.get("channel_id")

        if channel_id:
            channels = Channel.objects.filter(
                id=channel_id,
                channel_type=ChannelType.SLACK,
                is_active=True,
            )
            if not channels.exists():
                raise CommandError(f"Active Slack channel with ID {channel_id} not found")
        else:
            channels = Channel.objects.filter(
                channel_type=ChannelType.SLACK,
                is_active=True,
            )

        if not channels.exists():
            raise CommandError("No active Slack channels configured. Run setup_slack first.")

        channel = channels.first()
        self.stdout.write(f"Starting Slack bot daemon for channel: {channel.name}")  # type: ignore[union-attr]

        try:
            self._run_bot(channel)  # type: ignore[arg-type]
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nSlack bot daemon stopped."))

    def _run_bot(self, channel: Channel) -> None:
        try:
            from slack_bolt import App  # noqa: PLC0415
        except ImportError as err:
            raise CommandError("slack-bolt not installed. Run: uv add slack-bolt") from err

        bot_token, app_token, signing_secret = self._get_credentials(channel)
        use_socket_mode = channel.config.get("socket_mode", False)

        if use_socket_mode and not app_token:
            raise CommandError(f"Socket mode enabled but app_token not found for channel '{channel.name}'")

        app = App(token=bot_token, signing_secret=signing_secret)
        self._register_handlers(app)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.stdout.write(self.style.SUCCESS(f"Slack bot started for channel: {channel.name}"))
        self._start_bot(use_socket_mode, app, app_token)

    def _get_credentials(self, channel: Channel) -> tuple[str, str | None, str | None]:
        """Extract and validate credentials from channel."""
        try:
            credential = channel.channelcredential
            bot_token = credential.encrypted_data.get("bot_token")
            app_token = credential.encrypted_data.get("app_token")
            signing_secret = credential.encrypted_data.get("signing_secret")
        except Channel.channelcredential.RelatedObjectDoesNotExist:  # type: ignore[attr-defined]
            raise CommandError(f"No credentials found for channel '{channel.name}'") from None

        if not bot_token:
            raise CommandError(f"Bot token not found for channel '{channel.name}'")

        return bot_token, app_token, signing_secret

    def _register_handlers(self, app: App) -> None:
        """Register Slack event handlers."""
        say_type = Callable[..., None]
        ack_type = Callable[[], None]
        respond_type = Callable[..., None]

        @app.event("app_mention")
        def handle_mention(event: dict, say: say_type) -> None:
            user = event.get("user")
            text = event.get("text", "")
            logger.info("Received mention from %s: %s", user, text[:50])
            # TODO: Integrate with agent/LLM for actual response
            say(f"Hi <@{user}>! I received your message. (Agent integration pending)")

        @app.event("message")
        def handle_message(event: dict, say: say_type) -> None:
            if event.get("subtype") or event.get("bot_id"):
                return
            if event.get("channel_type") != "im":
                return
            user = event.get("user")
            text = event.get("text", "")
            logger.info("Received DM from %s: %s", user, text[:50])
            # TODO: Integrate with agent/LLM for actual response
            say(f"Received: {text}\n\n(Agent integration pending)")

        @app.command("/marvin")
        def handle_slash_command(ack: ack_type, respond: respond_type, command: dict) -> None:
            ack()
            text = command.get("text", "")
            user = command.get("user_id")
            logger.info("Received /marvin command from %s: %s", user, text[:50])
            # TODO: Integrate with agent/LLM for actual response
            respond(f"Received command: {text}\n\n(Agent integration pending)")

    def _start_bot(self, use_socket_mode: bool, app: App, app_token: str | None) -> None:
        """Start the bot in the appropriate mode."""
        if use_socket_mode:
            from slack_bolt.adapter.socket_mode import SocketModeHandler  # noqa: PLC0415

            self.stdout.write("Running in Socket Mode...")
            handler = SocketModeHandler(app, app_token)
            handler.start()
        else:
            self.stdout.write("Running in HTTP Mode...")
            self.stdout.write(
                self.style.WARNING("Note: HTTP mode requires a separate web server to handle webhook requests.")
            )
            self.stdout.write("Configure your Slack app to send events to: /slack/events")
            raise CommandError(
                "HTTP mode should be handled by the web server. "
                "Enable socket mode by adding an app_token, or configure webhook endpoints."
            )

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
        self.stdout.write("\nReceived shutdown signal...")
        self._shutdown = True
        sys.exit(0)
