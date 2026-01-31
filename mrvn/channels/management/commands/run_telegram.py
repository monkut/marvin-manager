import asyncio
import logging
import signal
from typing import TYPE_CHECKING

from django.core.management.base import BaseCommand, CommandError

from channels.models import Channel, ChannelType

if TYPE_CHECKING:
    from argparse import ArgumentParser

    from telegram import Update
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot daemon for processing messages"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._shutdown_event: asyncio.Event | None = None
        self._application = None

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--channel-id",
            type=int,
            help="Specific channel ID to run (default: run all active Telegram channels)",
        )

    def handle(self, *args, **options) -> None:
        channel_id = options.get("channel_id")

        if channel_id:
            channels = Channel.objects.filter(
                id=channel_id,
                channel_type=ChannelType.TELEGRAM,
                is_active=True,
            )
            if not channels.exists():
                raise CommandError(f"Active Telegram channel with ID {channel_id} not found")
        else:
            channels = Channel.objects.filter(
                channel_type=ChannelType.TELEGRAM,
                is_active=True,
            )

        if not channels.exists():
            raise CommandError("No active Telegram channels configured. Run setup_telegram first.")

        self.stdout.write(f"Starting Telegram bot daemon for {channels.count()} channel(s)...")

        # Run the async bot loop
        try:
            asyncio.run(self._run_bot(channels.first()))
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nTelegram bot daemon stopped."))

    async def _run_bot(self, channel: Channel) -> None:
        try:
            from telegram import Update  # noqa: PLC0415
            from telegram.ext import (  # noqa: PLC0415
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError as err:
            raise CommandError("python-telegram-bot not installed. Run: uv add python-telegram-bot") from err

        # Get bot token from credentials
        try:
            credential = channel.channelcredential
            bot_token = credential.encrypted_data.get("bot_token")
        except Channel.channelcredential.RelatedObjectDoesNotExist:  # type: ignore[attr-defined]
            raise CommandError(f"No credentials found for channel '{channel.name}'") from None

        if not bot_token:
            raise CommandError(f"Bot token not found in credentials for channel '{channel.name}'")

        # Build application
        application = Application.builder().token(bot_token).build()
        self._application = application

        # Register handlers
        application.add_handler(CommandHandler("start", self._handle_start))
        application.add_handler(CommandHandler("help", self._handle_help))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        self._shutdown_event = asyncio.Event()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        self.stdout.write(self.style.SUCCESS(f"Telegram bot started for channel: {channel.name}"))

        # Start polling
        await application.initialize()
        await application.start()

        # Use polling mode
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Graceful shutdown
        self.stdout.write("Shutting down Telegram bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

    def _signal_handler(self) -> None:
        if self._shutdown_event:
            self._shutdown_event.set()

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Hello! I'm Marvin, your AI assistant. Send me a message to get started.",
            )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if update.effective_chat:
            help_text = (
                "Available commands:\n"
                "/start - Start a conversation\n"
                "/help - Show this help message\n\n"
                "Just send me a message and I'll respond!"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.effective_chat:
            return

        user_message = update.message.text
        chat_id = update.effective_chat.id

        logger.info("Received message from chat %s: %s", chat_id, user_message[:50])

        # TODO: Integrate with agent/LLM for actual response
        # For now, echo back as placeholder
        response = f"Received: {user_message}\n\n(Agent integration pending)"

        await context.bot.send_message(chat_id=chat_id, text=response)
