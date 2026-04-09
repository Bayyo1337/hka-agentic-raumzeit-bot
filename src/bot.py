"""
Telegram Bot Entry Point.
Startet den Bot und leitet Nachrichten an den Claude-Agent weiter.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=settings.log_level,
)
log = logging.getLogger(__name__)

_BOT_START = datetime.now()

# Bot-Nachrichten-IDs pro Chat (für /reset → nur aktuelle Session, nicht persistent nötig)
_bot_messages: dict[int, list[int]] = {}

_USER_COMMANDS = [
    BotCommand("start", "Hilfe & Übersicht"),
    BotCommand("stats", "Deine Nutzungsstatistik"),
    BotCommand("reset", "Gesprächsverlauf löschen"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("rooms", "Alle Räume auflisten"),
    BotCommand("admin", "Nutzerübersicht (Admin)"),
]


def _is_allowed(user_id: int) -> bool:
    allowed = settings.allowed_ids
    return not allowed or user_id in allowed


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def _require_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Kein Zugriff.")
            return
        return await func(update, context)
    return wrapper


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_admin = _is_admin(user_id)
    admin_note = "\n\n🔧 Admin-Befehle:\n/rooms – Alle Räume auflisten\n/admin – Nutzerübersicht" if is_admin else ""
    text = (
        "🏫 Raumzeit-Bot\n\n"
        "Stell mir einfach eine Frage auf Deutsch, z.B.:\n"
        "  • Wann ist Raum M-001 heute frei?\n"
        "  • Zeig mir den Stundenplan von IWI_3\n"
        "  • Wann hat Dozent muster Zeit?\n\n"
        "Befehle:\n"
        "/stats – Deine Nutzungsstatistik\n"
        "/reset – Gesprächsverlauf löschen (KI-Gedächtnis)"
        + admin_note
    )
    msg = await update.message.reply_text(text)
    _bot_messages.setdefault(update.effective_chat.id, []).append(msg.message_id)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await db.clear_history(chat_id)

    deleted = 0
    for msg_id in _bot_messages.pop(chat_id, []):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except Exception:
            pass

    try:
        await update.message.delete()
    except Exception:
        pass

    msg = await context.bot.send_message(chat_id, f"🗑 Chat geleert ({deleted} Nachrichten entfernt).")
    _bot_messages.setdefault(chat_id, []).append(msg.message_id)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    limit = settings.rate_limit_per_hour
    recent = await db.get_recent_count(user_id)
    total = await db.get_total_count(user_id)
    tok_in, tok_out = await db.get_tokens(user_id)
    history = await db.load_history(update.effective_chat.id)
    history_len = len(history) // 2
    remaining = (limit - recent) if limit > 0 else "∞"

    # Wann wird das Limit zurückgesetzt?
    reset_info = ""
    if limit and recent >= limit:
        oldest = await db.get_oldest_recent_ts(user_id)
        if oldest:
            reset_at = oldest + timedelta(hours=1)
            mins = max(0, int((reset_at - datetime.now()).total_seconds() / 60))
            reset_info = f"\nLimit-Reset in: ~{mins} min"

    await update.message.reply_text(
        f"📊 Deine Statistik\n"
        f"Anfragen letzte Stunde: {recent}/{limit if limit else '∞'}\n"
        f"Noch verfügbar: {remaining}{reset_info}\n"
        f"Gesamt: {total} Anfragen\n"
        f"Tokens: {tok_in + tok_out:,} (↑{tok_in:,} / ↓{tok_out:,})\n"
        f"Gesprächsverlauf: {history_len} Austausch(e)",
    )


@_require_admin
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now()
    limit = settings.rate_limit_per_hour

    uptime = now - _BOT_START
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m = rem // 60

    user_ids = await db.get_all_user_ids()
    all_tokens = await db.get_all_tokens()

    tok_in_all = sum(v[0] for v in all_tokens.values())
    tok_out_all = sum(v[1] for v in all_tokens.values())
    total_all = sum([await db.get_total_count(uid) for uid in user_ids])

    lines = [
        f"📋 Admin-Übersicht",
        f"Uptime: {h}h {m}min  |  Provider: {settings.llm_provider}",
        f"Anfragen gesamt: {total_all}  |  Tokens: {tok_in_all + tok_out_all:,}",
        f"  ↳ Input: {tok_in_all:,}  |  Output: {tok_out_all:,}",
        "",
    ]

    if not user_ids:
        lines.append("Noch keine Nutzerdaten vorhanden.")
    else:
        lines.append("Nutzer:")
        for uid in user_ids:
            recent = await db.get_recent_count(uid)
            total = await db.get_total_count(uid)
            tok_in, tok_out = all_tokens.get(uid, (0, 0))
            tok = tok_in + tok_out

            reset_info = ""
            if limit and recent >= limit:
                oldest = await db.get_oldest_recent_ts(uid)
                if oldest:
                    mins = max(0, int((oldest + timedelta(hours=1) - now).total_seconds() / 60))
                    reset_info = f" (reset ~{mins}min)"
            elif limit:
                reset_info = f" ({limit - recent} frei)"

            lines.append(f"👤 {uid}  {recent}/{limit if limit else '∞'}/h{reset_info}  |  {total} ges.  |  {tok:,} tok")

    await update.message.reply_text("\n".join(lines))


@_require_admin
async def cmd_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Lade Raumliste...")
    try:
        rooms = await raumzeit.get_all_rooms()
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Fehler: {exc}")
        return

    names: list[str] = []
    for r in rooms:
        if isinstance(r, dict):
            name = r.get("name") or r.get("shortName") or r.get("longName", "")
        else:
            name = str(r)
        if name:
            names.append(name)

    names.sort()
    text = "🏫 Verfügbare Räume:\n" + ", ".join(names)
    if len(text) > 4000:
        text = text[:4000] + "…"
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    if not _is_allowed(user_id):
        log.warning("Blocked unauthorized user %d", user_id)
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Bot zu nutzen.")
        return

    limit = settings.rate_limit_per_hour
    allowed = await db.check_rate_limit(user_id, limit)
    if not allowed:
        oldest = await db.get_oldest_recent_ts(user_id)
        if oldest:
            mins = max(0, int((oldest + timedelta(hours=1) - datetime.now()).total_seconds() / 60))
            reset_info = f" Limit-Reset in ~{mins} min."
        else:
            reset_info = ""
        await update.message.reply_text(
            f"⏳ Du hast das Limit von {limit} Anfragen/Stunde erreicht.{reset_info}"
        )
        return

    log.info("Anfrage von user=%d chat=%d: %s", user_id, chat_id, text)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    history = await db.load_history(chat_id)
    try:
        reply, tok_in, tok_out = await agent.run(text, history)
        await db.save_history(chat_id, history)
        await db.add_tokens(user_id, tok_in, tok_out)
    except Exception as exc:
        log.exception("Agent-Fehler")
        await update.message.reply_text(
            "⚠️ Fehler bei der KI-Anfrage. Bitte kurz warten und nochmal versuchen.\n"
            f"Details: {exc}"
        )
        return

    try:
        msg = await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception:
        # Markdown ungültig → Plain Text
        log.warning("Markdown-Fehler, sende als Plain Text")
        try:
            msg = await update.message.reply_text(reply)
        except Exception:
            log.exception("Fehler beim Senden der Antwort")
            return
    _bot_messages.setdefault(chat_id, []).append(msg.message_id)


async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    log.info("Bot-Commands registriert, DB bereit")


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("rooms", cmd_rooms))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot gestartet, warte auf Nachrichten...")
    app.run_polling()


if __name__ == "__main__":
    main()
