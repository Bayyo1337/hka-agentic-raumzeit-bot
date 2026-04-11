"""
Telegram Bot Entry Point.
Modularisiert: Routing und User-Interaktion.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db
from src import formatter
from src import admin
from src import terminal
from src.formatter import CONFIRM_SENTINEL
from src.state import _maintenance, _personal_features

# Logging Setup
from rich.logging import RichHandler
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=terminal.console, show_path=False)]
)

def set_log_level(level_name: str) -> bool:
    """Ändert das Log-Level aller relevanten Logger zur Laufzeit."""
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        return False
    for _name in ("src.bot", "src.agent", "src.tools", "src.db", "src.formatter"):
        logging.getLogger(_name).setLevel(level)
    return True

set_log_level(settings.log_level)
log = logging.getLogger("src.bot")

# In-Memory State für Telegram
_bot_messages: dict[int, list[int]] = {}
_pending_confirmation: dict[int, tuple[str, str, int, str | None]] = {}

_NEIN = {"nein", "ne", "n", "no", "falsch", "stimmt nicht", "stimmt nicht so", "nope"}
_JA   = {"ja", "j", "yes", "y", "stimmt", "korrekt", "ok", "okay"}

_USER_COMMANDS = [
    BotCommand("start", "Hilfe & Übersicht"),
    BotCommand("setcourse", "Eigener Stundenplan festlegen"),
    BotCommand("stats", "Deine Nutzungsstatistik"),
    BotCommand("reset", "Gesprächsverlauf löschen"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("admin", "Nutzer- & System-Übersicht"),
    BotCommand("rooms", "Alle Räume auflisten"),
    BotCommand("sync", "Kurs-Index neu aufbauen"),
    BotCommand("ping", "API-Erreichbarkeit prüfen"),
    BotCommand("indexage", "Alter des Kurs-Index"),
    BotCommand("courses", "Kurs-Index für ein Kürzel"),
    BotCommand("feedback", "Feedback-Logs auflisten"),
    BotCommand("user", "Detailansicht eines Nutzers"),
    BotCommand("ban", "Nutzer sperren"),
    BotCommand("unban", "Nutzer entsperren"),
    BotCommand("resetlimit", "Rate-Limit-Zähler zurücksetzen"),
    BotCommand("cleartokens", "Token-Zähler zurücksetzen"),
    BotCommand("clearhistory", "Gesprächsverlauf eines Nutzers löschen"),
    BotCommand("broadcast", "Nachricht an alle Nutzer senden"),
    BotCommand("setprovider", "LLM-Provider wechseln"),
    BotCommand("loglevel", "Log-Level ändern (info|debug|warning)"),
    BotCommand("togglepersonal", "Personalisierung (/setcourse) an/aus"),
    BotCommand("maintenance", "Wartungsmodus ein-/ausschalten"),
]

def _is_allowed(user_id: int) -> bool:
    return not settings.allowed_ids or user_id in settings.allowed_ids

def _command_help(is_admin: bool) -> str:
    lines = ["📋 Befehle:", "/start – Hilfe", "/stats – Statistik", "/reset – Verlauf löschen"]
    if _personal_features[0]:
        lines.insert(2, "/setcourse – Eigener Studiengang")
    if is_admin:
        lines += ["", "🔧 Admin:", "/admin, /rooms, /sync, /ping, /indexage, /user, /ban, /loglevel, /maintenance"]
    return "\n".join(lines)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_admin = admin._is_admin(user_id)
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
    for mid in _bot_messages.pop(chat_id, []):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            deleted += 1
        except: pass
    msg = await context.bot.send_message(chat_id, f"🗑 Chat geleert ({deleted} Nachrichten entfernt).")
    _bot_messages.setdefault(chat_id, []).append(msg.message_id)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    limit = settings.rate_limit_per_hour
    recent = await db.get_recent_count(user_id)
    total = await db.get_total_count(user_id)
    tok_in, tok_out = await db.get_tokens(user_id)
    history = await db.load_history(update.effective_chat.id)
    history_len = len(history) // 2
    remaining = (limit - recent) if limit > 0 else "∞"
    course_str = f"\nKurs: {u['primary_course']}" if u and u.get("primary_course") else ""
    
    await update.message.reply_text(
        f"📊 Deine Statistik{course_str}\n"
        f"Anfragen letzte Stunde: {recent}/{limit if limit else '∞'}\n"
        f"Noch verfügbar: {remaining}\nGesamt: {total} Anfragen\n"
        f"Tokens: {tok_in + tok_out:,}\nGesprächsverlauf: {history_len} Austausch(e)"
    )


async def cmd_setcourse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Interaktiver Assistent zum Festlegen des eigenen Studiengangs."""
    if not _personal_features[0]:
        await update.message.reply_text("💡 Dieses Feature ist aktuell deaktiviert.")
        return
    try:
        faculties = await raumzeit.get_departments()
        keyboard = []
        for f in faculties:
            name = f.get("name") or f.get("shortName", "Unknown")
            keyboard.append([InlineKeyboardButton(name, callback_data=f"setc_fac:{f['id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Wähle deine Fakultät:", reply_markup=reply_markup)
    except Exception as e:
        log.exception("Fehler in cmd_setcourse")
        await update.message.reply_text(f"⚠️ Fehler beim Laden der Fakultäten: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet die Klicks auf die Inline-Buttons des setcourse-Assistenten."""
    query = update.callback_query
    await query.answer()
    
    if not _personal_features[0]:
        await query.edit_message_text("💡 Dieses Feature wurde deaktiviert.")
        return

    data = query.data

    if data.startswith("setc_fac:"):
        fac_id = data.split(":")[1]
        try:
            courses = await raumzeit.get_courses_of_study(fac_id)
            keyboard = []
            for c in courses:
                name = c.get("name") or c.get("shortName", "Unknown")
                keyboard.append([InlineKeyboardButton(name, callback_data=f"setc_deg:{c['name']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Wähle deinen Studiengang:", reply_markup=reply_markup)
        except Exception as e:
            await query.edit_message_text(f"⚠️ Fehler: {e}")

    elif data.startswith("setc_deg:"):
        deg_abbr = data.split(":")[1]
        keyboard = []
        for i in range(1, 8, 2):
            row = [InlineKeyboardButton(f"Sem. {i}", callback_data=f"setc_fin:{deg_abbr}.{i}")]
            if i + 1 <= 7:
                row.append(InlineKeyboardButton(f"Sem. {i+1}", callback_data=f"setc_fin:{deg_abbr}.{i+1}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Welches Semester ({deg_abbr})?", reply_markup=reply_markup)

    elif data.startswith("setc_fin:"):
        full_key = data.split(":")[1]
        await db.set_primary_course(update.effective_user.id, full_key)
        await query.edit_message_text(f"✅ Dein Stundenplan wurde auf *{full_key}* gesetzt.", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user
    text = update.message.text

    if not _is_allowed(user_id):
        log.warning("Blocked unauthorized user %d", user_id)
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Bot zu nutzen.")
        return

    await db.upsert_user(user_id, user.username or "", user.first_name or "")

    if not admin._is_admin(user_id) and await db.is_banned(user_id):
        await update.message.reply_text("⛔ Du wurdest gesperrt.")
        return

    if _maintenance[0] and not admin._is_admin(user_id):
        await update.message.reply_text(_maintenance[1])
        return

    custom_limit = await db.get_custom_rate_limit(user_id)
    limit = custom_limit if custom_limit >= 0 else settings.rate_limit_per_hour
    if not await db.check_rate_limit(user_id, limit):
        await update.message.reply_text(f"⏳ Du hast das Limit von {limit} Anfragen/Stunde erreicht.")
        return

    # Bestätigungsfrage auswerten (Eskalations-Logik)
    if chat_id in _pending_confirmation:
        normalized = text.strip().lower()
        original_query, course_key, stufe, queried_date = _pending_confirmation.pop(chat_id)
        if normalized in _JA:
            await update.message.reply_text("👍 Alles klar.")
            return
        if normalized in _NEIN or stufe >= 2:
            if stufe == 1:
                msg = await update.message.reply_text("🔄 Suche alle Varianten...")
                _bot_messages.setdefault(chat_id, []).append(msg.message_id)
                try:
                    result = await raumzeit.fetch_course_brute_force(course_key, queried_date)
                    reply = formatter.format_results([("get_course_timetable", result)], original_query)
                except Exception as exc:
                    await msg.edit_text(f"⚠️ Fehler: {exc}"); return
                if CONFIRM_SENTINEL in reply:
                    reply = reply.replace(CONFIRM_SENTINEL, "❓ Wie wirst du in Raumzeit angezeigt?\nGib deinen genauen Kurs-Key ein (z.B. `MABB.6.DF`).")
                    _pending_confirmation[chat_id] = (original_query, course_key, 2, queried_date)
                await msg.edit_text(reply, parse_mode="Markdown")
                return
            elif stufe == 2:
                if normalized in _NEIN: stufe = 3
                else:
                    user_key = text.strip().upper().replace("_", ".")
                    try:
                        result = await raumzeit.get_course_timetable(user_key, queried_date)
                        reply = formatter.format_results([("get_course_timetable", result)], original_query)
                    except Exception as exc:
                        await update.message.reply_text(f"⚠️ Fehler: {exc}"); return
                    if CONFIRM_SENTINEL in reply: stufe = 3
                    else: await _send_reply(update, chat_id, reply); return
            if stufe >= 3:
                await update.message.reply_text("😕 Keine Daten gefunden. Deine Anfrage wurde für manuelle Prüfung gespeichert.")
                return

    user_label = f"@{user.username}" if user.username else str(user_id)
    log.debug("Anfrage von %s (chat=%d): %.80s", user_label, chat_id, text)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Nutzer-Profil laden (für persönlichen Stundenplan)
    u = await db.get_user(user_id)
    primary_course = u.get("primary_course") if u else None

    history = await db.load_history(chat_id)
    try:
        reply, tok_in, tok_out, collected_results = await agent.run(
            text, history, user_label=user_label, primary_course=primary_course
        )
        await db.save_history(chat_id, history)
        await db.add_tokens(user_id, tok_in, tok_out)
        if CONFIRM_SENTINEL in reply:
            course = next((r.get("course_semester", "") for n, r in collected_results if n == "get_course_timetable"), "")
            queried_date = next((r.get("queried_date") for n, r in collected_results if n == "get_course_timetable"), None)
            raw_date = queried_date if (queried_date and len(queried_date) == 10) else None
            _pending_confirmation[chat_id] = (text, course, 1, raw_date)
        await _send_reply(update, chat_id, reply)
    except Exception as exc:
        log.exception("Agent-Fehler"); await update.message.reply_text(f"⚠️ Fehler: {exc}")

async def _send_reply(update, chat_id: int, reply: str) -> None:
    try: msg = await update.message.reply_text(reply, parse_mode="Markdown")
    except: msg = await update.message.reply_text(reply)
    _bot_messages.setdefault(chat_id, []).append(msg.message_id)

async def _run_index_build():
    try: n = await raumzeit.build_course_index(); log.info("Kurs-Index: %d Einträge", n)
    except: log.exception("Kurs-Index failed")

async def _run_lecturer_build():
    try: n = await raumzeit.build_lecturer_index(); log.info("Dozenten-Index: %d Matches", n)
    except: log.exception("Dozenten-Index failed")

async def _weekly_lecturer_refresh():
    while True: await asyncio.sleep(7*24*3600); await _run_lecturer_build()

async def _error_handler(u, c):
    if not isinstance(c.error, NetworkError): log.exception("Unbehandelter Fehler", exc_info=c.error)

async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    for aid in settings.admin_ids:
        try: await app.bot.set_my_commands(_ADMIN_COMMANDS, scope={"type": "chat", "chat_id": aid})
        except: pass
    if await db.course_index_stale(): asyncio.create_task(_run_index_build())
    if raumzeit.lecturers_stale(): asyncio.create_task(_run_lecturer_build())
    else: raumzeit.load_lecturers()
    asyncio.create_task(_weekly_lecturer_refresh())

async def main_async() -> None:
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("setcourse", cmd_setcourse))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("admin", admin.cmd_admin))
    app.add_handler(CommandHandler("rooms", admin.cmd_rooms))
    app.add_handler(CommandHandler("sync", admin.cmd_sync))
    app.add_handler(CommandHandler("ping", admin.cmd_ping))
    app.add_handler(CommandHandler("indexage", admin.cmd_indexage))
    app.add_handler(CommandHandler("courses", admin.cmd_courses))
    app.add_handler(CommandHandler("feedback", admin.cmd_feedback))
    app.add_handler(CommandHandler("delfeedback", admin.cmd_delfeedback))
    app.add_handler(CommandHandler("user", admin.cmd_user))
    app.add_handler(CommandHandler("ban", admin.cmd_ban))
    app.add_handler(CommandHandler("unban", admin.cmd_unban))
    app.add_handler(CommandHandler("resetlimit", admin.cmd_resetlimit))
    app.add_handler(CommandHandler("setlimit", admin.cmd_setlimit))
    app.add_handler(CommandHandler("cleartokens", admin.cmd_cleartokens))
    app.add_handler(CommandHandler("clearhistory", admin.cmd_clearhistory_admin))
    app.add_handler(CommandHandler("broadcast", admin.cmd_broadcast))
    app.add_handler(CommandHandler("setprovider", admin.cmd_setprovider))
    app.add_handler(CommandHandler("loglevel", admin.cmd_loglevel))
    app.add_handler(CommandHandler("togglepersonal", admin.cmd_togglepersonal))
    app.add_handler(CommandHandler("maintenance", admin.cmd_maintenance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)

    await app.initialize(); await app.start(); await app.updater.start_polling()
    stop_event = asyncio.Event()
    
    # Dashboard einmalig beim Start anzeigen
    terminal.console.print(terminal.make_dashboard())
    
    # Interaktive Konsole starten (ohne Live-Update, da input() blockiert)
    await terminal.terminal_loop(app, stop_event)
    
    await app.updater.stop(); await app.stop(); await app.shutdown()

def main():
    try: asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit): pass

if __name__ == "__main__": main()
