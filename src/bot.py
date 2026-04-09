"""
Telegram Bot Entry Point.
Startet den Bot und leitet Nachrichten an den Claude-Agent weiter.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
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

# Rate Limiting: user_id → Liste von Request-Zeitstempeln
_request_log: dict[int, list[datetime]] = defaultdict(list)


def _is_allowed(user_id: int) -> bool:
    allowed = settings.allowed_ids
    return not allowed or user_id in allowed


def _check_rate_limit(user_id: int) -> bool:
    """True wenn der User noch im Limit ist."""
    limit = settings.rate_limit_per_hour
    if limit == 0:
        return True
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    # Alte Einträge entfernen
    _request_log[user_id] = [t for t in _request_log[user_id] if t > cutoff]
    if len(_request_log[user_id]) >= limit:
        return False
    _request_log[user_id].append(now)
    return True


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
    user_id = update.effective_user.id
    text = update.message.text

    if not _is_allowed(user_id):
        log.warning("Blocked unauthorized user %d", user_id)
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Bot zu nutzen.")
        return

    if not _check_rate_limit(user_id):
        remaining = settings.rate_limit_per_hour
        await update.message.reply_text(
            f"⏳ Du hast das Limit von {remaining} Anfragen/Stunde erreicht. Bitte warte etwas."
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    history = _histories.setdefault(chat_id, [])
    try:
        reply = await agent.run(text, history)
    except Exception as exc:
        log.exception("Agent-Fehler")
        await update.message.reply_text(
            "⚠️ Fehler bei der KI-Anfrage. Bitte kurz warten und nochmal versuchen.\n"
            f"Details: {exc}"
        )
        return

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
