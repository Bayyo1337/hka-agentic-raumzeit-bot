"""
Telegram Bot Entry Point.
Startet den Bot und leitet Nachrichten an den Claude-Agent weiter.
"""

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from src.config import settings
from src import agent

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=settings.log_level,
)
log = logging.getLogger(__name__)

# Pro Chat eine einfache In-Memory-History (für Produktiv: Redis o.ä.)
_histories: dict[int, list[dict]] = {}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hallo! Ich helfe dir beim Buchen von Räumen über Raumzeit. "
        "Schreib einfach, was du brauchst."
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Gesprächsverlauf zurückgesetzt.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    history = _histories.setdefault(chat_id, [])
    reply = await agent.run(text, history)

    # History wird in agent.run bereits befüllt; wir halten nur die Referenz
    await update.message.reply_text(reply)


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot gestartet, warte auf Nachrichten...")
    app.run_polling()


if __name__ == "__main__":
    main()
