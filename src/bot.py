"""
Telegram Bot Entry Point.
Startet den Bot und leitet Nachrichten an den Claude-Agent weiter.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db
from src import formatter

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.WARNING,
)
# Nur eigene Logger auf den konfigurierten Level setzen
for _name in ("src.bot", "src.agent", "src.tools", "src.db", "src.formatter"):
    logging.getLogger(_name).setLevel(settings.log_level)
log = logging.getLogger(__name__)

_BOT_START = datetime.now()

# Bot-Nachrichten-IDs pro Chat (für /reset → nur aktuelle Session, nicht persistent nötig)
_bot_messages: dict[int, list[int]] = {}

# Offene Bestätigungsfragen: chat_id → (original_query, course_key, stufe, queried_date)
# stufe: 1=Brute-Force, 2=User-Key-Eingabe, 3=aufgeben
_pending_confirmation: dict[int, tuple[str, str, int, str | None]] = {}

_NEIN = {"nein", "ne", "n", "no", "falsch", "stimmt nicht", "stimmt nicht so", "nope"}
_JA   = {"ja", "j", "yes", "y", "stimmt", "korrekt", "ok", "okay"}

_USER_COMMANDS = [
    BotCommand("start", "Hilfe & Übersicht"),
    BotCommand("stats", "Deine Nutzungsstatistik"),
    BotCommand("reset", "Gesprächsverlauf löschen"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("rooms", "Alle Räume auflisten"),
    BotCommand("admin", "Nutzerübersicht (Admin)"),
    BotCommand("sync", "Kurs-Index neu aufbauen (Admin)"),
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


def _command_help(is_admin: bool) -> str:
    lines = [
        "📋 Befehle:",
        "/start – Diese Hilfe anzeigen",
        "/stats – Deine Nutzungsstatistik",
        "/reset – Gesprächsverlauf löschen",
    ]
    if is_admin:
        lines += [
            "",
            "🔧 Admin:",
            "/admin – Nutzer- & System-Übersicht",
            "/rooms – Alle Räume auflisten",
            "/sync – Kurs-Index neu aufbauen",
        ]
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_admin = _is_admin(user_id)
    text = (
        "🏫 Raumzeit-Bot\n\n"
        "Stell mir einfach eine Frage auf Deutsch, z.B.:\n"
        "  • Wann ist Raum M-001 heute frei?\n"
        "  • Zeig mir den Stundenplan von MABB Semester 7\n"
        "  • Wann hat Dozent muster Zeit?\n\n"
        + _command_help(is_admin)
    )
    msg = await update.message.reply_text(text)
    _bot_messages.setdefault(update.effective_chat.id, []).append(msg.message_id)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await db.clear_history(chat_id)
    _pending_confirmation.pop(chat_id, None)

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
    index_count = await db.get_course_index_count()

    tok_in_all = sum(v[0] for v in all_tokens.values())
    tok_out_all = sum(v[1] for v in all_tokens.values())
    total_all = sum([await db.get_total_count(uid) for uid in user_ids])

    lines = [
        f"📋 Admin-Übersicht",
        f"Uptime: {h}h {m}min  |  Provider: {settings.llm_provider}",
        f"Anfragen gesamt: {total_all}  |  Tokens: {tok_in_all + tok_out_all:,}",
        f"  ↳ Input: {tok_in_all:,}  |  Output: {tok_out_all:,}",
        f"Kurs-Index: {index_count} Einträge",
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

    lines.append("")
    lines.append(_command_help(is_admin=True))
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


@_require_admin
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Kurs-Index wird neu aufgebaut...")
    try:
        count = await raumzeit.build_course_index()
        await msg.edit_text(f"✅ Kurs-Index neu aufgebaut: {count} Einträge gefunden.")
    except Exception as exc:
        log.exception("Kurs-Index Aufbau fehlgeschlagen")
        await msg.edit_text(f"⚠️ Fehler beim Index-Aufbau: {exc}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user
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

    # Token-Limit prüfen (Admins ausgenommen)
    token_limit = settings.max_tokens_per_user
    if token_limit and not _is_admin(user_id):
        tok_in, tok_out = await db.get_tokens(user_id)
        if tok_in + tok_out >= token_limit:
            await update.message.reply_text(
                f"⛔ Du hast dein Token-Limit von {token_limit:,} erreicht. Bitte wende dich an den Admin."
            )
            return

    # Bestätigungsfrage auswerten (3-stufige Eskalation)
    if chat_id in _pending_confirmation:
        normalized = text.strip().lower()
        original_query, course_key, stufe, queried_date = _pending_confirmation.pop(chat_id)

        if normalized in _JA:
            await update.message.reply_text("👍 Alles klar.")
            return

        if normalized in _NEIN or stufe >= 2:
            if stufe == 1:
                # Stufe 1: Brute-Force alle Suffixe für diesen Kurs
                msg = await update.message.reply_text("🔄 Suche alle Varianten für diesen Kurs...")
                _bot_messages.setdefault(chat_id, []).append(msg.message_id)
                try:
                    result = await raumzeit.fetch_course_brute_force(course_key, queried_date)
                    reply = formatter.format_results([("get_course_timetable", result)], original_query)
                except Exception as exc:
                    await msg.edit_text(f"⚠️ Fehler: {exc}")
                    return
                if "Stimmt das so?" in reply:
                    # Immer noch leer → Stufe 2
                    reply = reply.replace(
                        "❓ Stimmt das so? (ja / nein)",
                        "❓ Wie wirst du in Raumzeit angezeigt?\n"
                        "Gib deinen genauen Kurs-Key ein (z.B. `MABB.6.DF`) oder schreibe *nein* zum Abbrechen."
                    )
                    _pending_confirmation[chat_id] = (original_query, course_key, 2, queried_date)
                try:
                    await msg.edit_text(reply, parse_mode="Markdown")
                except Exception:
                    await msg.edit_text(reply)
                return

            elif stufe == 2:
                if normalized in _NEIN:
                    stufe = 3
                else:
                    # User hat einen Key eingegeben → direkt abfragen
                    user_key = text.strip().upper().replace("_", ".")
                    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                    try:
                        result = await raumzeit.get_course_timetable(user_key, queried_date)
                        reply = formatter.format_results([("get_course_timetable", result)], original_query)
                    except Exception as exc:
                        await update.message.reply_text(f"⚠️ Fehler: {exc}")
                        return
                    if "Stimmt das so?" in reply:
                        stufe = 3
                    else:
                        await _send_reply(update, chat_id, reply)
                        return

            if stufe >= 3:
                # Aufgeben + Feedback-Log speichern
                log_data = {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "query": original_query,
                    "course_key": course_key,
                    "queried_date": queried_date,
                    "ts": datetime.now().isoformat(),
                }
                try:
                    path = await db.save_feedback_log(chat_id, log_data)
                    log.warning("Feedback-Log gespeichert: %s", path)
                except Exception:
                    log.exception("Feedback-Log konnte nicht gespeichert werden")
                await update.message.reply_text(
                    "😕 Ich konnte keine Daten für diesen Kurs finden.\n"
                    "Deine Anfrage wurde gespeichert – wir schauen uns das manuell an."
                )
                return
        # Unklare Antwort → normal weiterverarbeiten (kein return)

    user_label = f"@{user.username}" if user.username else str(user_id)
    log.debug("Anfrage von %s (chat=%d): %.80s", user_label, chat_id, text)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    history = await db.load_history(chat_id)
    try:
        reply, tok_in, tok_out, collected_results = await agent.run(text, history, user_label=user_label)
        await db.save_history(chat_id, history)
        await db.add_tokens(user_id, tok_in, tok_out)
    except Exception as exc:
        log.exception("Agent-Fehler")
        await update.message.reply_text(
            "⚠️ Fehler bei der KI-Anfrage. Bitte kurz warten und nochmal versuchen.\n"
            f"Details: {exc}"
        )
        return

    # Bestätigungsfrage merken wenn Formatter sie eingefügt hat
    if "Stimmt das so?" in reply:
        course_key = next(
            (r.get("course_semester", "") for n, r in collected_results if n == "get_course_timetable"),
            ""
        )
        queried_date = next(
            (r.get("queried_date") for n, r in collected_results if n == "get_course_timetable"),
            None
        )
        # queried_date ist ggf. "KW 15 (...)" → kein direktes Datum, None nutzen
        raw_date = queried_date if (queried_date and len(queried_date) == 10) else None
        _pending_confirmation[chat_id] = (text, course_key, 1, raw_date)

    await _send_reply(update, chat_id, reply)


async def _send_reply(update, chat_id: int, reply: str) -> None:
    """Sendet eine Antwort mit Markdown-Fallback und merkt die Nachrichten-ID."""
    try:
        msg = await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception:
        log.warning("Markdown-Fehler, sende als Plain Text")
        try:
            msg = await update.message.reply_text(reply)
        except Exception:
            log.exception("Fehler beim Senden der Antwort")
            return
    _bot_messages.setdefault(chat_id, []).append(msg.message_id)


async def _run_index_build() -> None:
    try:
        count = await raumzeit.build_course_index()
        log.info("Kurs-Index: Aufbau abgeschlossen, %d Einträge", count)
    except Exception:
        log.exception("Kurs-Index: Aufbau fehlgeschlagen")


async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    log.info("Bot-Commands registriert, DB bereit")

    if await db.course_index_stale():
        log.info("Kurs-Index: veraltet oder leer – starte Aufbau im Hintergrund")
        asyncio.create_task(_run_index_build())
    else:
        count = await db.get_course_index_count()
        log.info("Kurs-Index: %d Einträge im Cache", count)


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
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot gestartet, warte auf Nachrichten...")
    app.run_polling()


if __name__ == "__main__":
    main()
