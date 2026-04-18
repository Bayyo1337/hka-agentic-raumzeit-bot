"""
Telegram Bot Entry Point.
Modularisiert: Routing und User-Interaktion.
"""

import asyncio
import logging
import sys
import os
import json
import traceback
import uuid
from datetime import datetime, timedelta, time as _time
from logging.handlers import RotatingFileHandler

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
from src.state import _maintenance, _personal_features, _map_feature

# Daemon-Erkennung
IS_DAEMON = not sys.stdout.isatty() or os.environ.get("RUN_AS_DAEMON") == "1"

# Watchdog State
_consecutive_network_errors = 0
NETWORK_ERROR_THRESHOLD = 15  # Nach 15 Fehlern in Folge Neustart erzwingen

# Logging Setup
from rich.logging import RichHandler

# 1. File Logging (Detailed, Rotating)
os.makedirs("logs", exist_ok=True)
log_file = "logs/bot.txt"
# Sicherstellen, dass die Datei existiert (als .txt wie gewünscht)
if not os.path.exists(log_file):
    with open(log_file, "a") as f: pass

file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

if IS_DAEMON:
    # Standard-Logging für Systemd (sauber ohne ANSI-Farben)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), file_handler]
    )
else:
    # Rich-Logging für interaktive Nutzung
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=False, console=terminal.console, show_path=False), file_handler]
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
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("src.bot")

# In-Memory State für Telegram
_bot_messages: dict[int, list[int]] = {}
_pending_confirmation: dict[int, tuple[str, str, int, str | None]] = {}
_error_cache: dict[str, dict] = {}

_NEIN = {"nein", "ne", "n", "no", "falsch", "stimmt nicht", "stimmt nicht so", "nope"}
_JA   = {"ja", "j", "yes", "y", "stimmt", "korrekt", "ok", "okay"}

_USER_COMMANDS = [
    BotCommand("start", "Einführung & Kurzhilfe"),
    BotCommand("help", "Ausführliche Hilfe & Beispiele"),
    BotCommand("myplan", "Dein persönlicher Stundenplan"),
    BotCommand("setcourse", "Eigener Studiengang hinterlegen"),
    BotCommand("stats", "Nutzungsstatistik & Profil"),
    BotCommand("reset", "Gesprächsverlauf löschen"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("admin", "System- & Nutzerübersicht"),
    BotCommand("sync", "Datenbank-Abgleich mit HKA"),
    BotCommand("togglepersonal", "Feature: Personalisierung an/aus"),
    BotCommand("togglemap", "Feature: Lageplan an/aus"),
    BotCommand("loglevel", "Logging-Detailtiefe ändern"),
    BotCommand("maintenance", "Wartungsmodus steuern"),
    BotCommand("broadcast", "Nachricht an alle Nutzer"),
]

def _is_allowed(user_id: int) -> bool:
    return not settings.allowed_ids or user_id in settings.allowed_ids

def _command_help(is_admin: bool) -> str:
    from src.state import _personal_features
    lines = [
        "📖 *Raumzeit KI-Bot Hilfe*",
        "",
        "Du kannst mich einfach in natürlicher Sprache fragen. Hier sind einige Beispiele:",
        "• *Räume:* \"Wann ist M-102 heute frei?\" oder \"Wo ist Gebäude E?\"",
        "• *Kurse:* \"Stundenplan MABB Semester 7\" oder \"Was habe ich am Mittwoch?\"",
        "• *Dozenten:* \"Wo unterrichtet Peter Offermann?\"",
        "• *Kalender:* \"Wann sind die nächsten Prüfungen?\"",
        "",
    ]
    if _personal_features[0]:
        lines.append("💡 *Tipp:* Nutze `/setcourse`, um deine Semester zu speichern. Dann weiß ich bei Fragen wie \"Was habe ich heute?\" automatisch, welcher Plan gemeint ist.\n")
    
    lines += [
        "📜 *Befehle:*",
        "/help – Diese ausführliche Hilfe",
        "/stats – Deine Tokens, Limits und gespeicherten Kurse",
        "/reset – Löscht den aktuellen Gesprächskontext",
    ]
    if _personal_features[0]:
        lines.insert(-2, "/myplan – Dein persönlicher Wochenstundenplan")
        lines.insert(-2, "/setcourse – Geführte Auswahl deines Studiengangs")

    if is_admin:
        lines += [
            "",
            "🔧 *Admin-Befehle:*",
            "/admin – Volle System-Übersicht",
            "/sync – Kurs- und Dozenten-Daten neu laden",
            "/togglepersonal – /setcourse Feature an/aus",
            "/togglemap – /togglemap Feature an/aus",
            "/loglevel <level> – Debug-Modus steuern",
            "/broadcast <text> – Nachricht an alle senden",
        ]
    return "\n".join(lines)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    is_admin = admin._is_admin(update.effective_user.id)
    await update.message.reply_text(_command_help(is_admin), parse_mode="Markdown")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_admin = admin._is_admin(user_id)
    text = (
        "🏫 *Raumzeit-Bot*\n\n"
        "Stell mir einfach eine Frage auf Deutsch, z.B.:\n"
        "• Wann ist Raum M-102 heute frei?\n"
        "• Wo ist das Gebäude LI?\n"
        "• Zeig mir den Stundenplan von MABB Semester 7\n\n"
        + _command_help(is_admin)
        + "\n\n📄 [Quellcode (AGPL-3.0)](https://github.com/Bayyo1337/hka-agentic-raumzeit-bot)"
    )
    msg = await update.message.reply_text(text, parse_mode="Markdown")
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
    
    course_raw = u.get("primary_course") if u else None
    try:
        courses = json.loads(course_raw) if course_raw else []
        if not isinstance(courses, list): courses = [str(courses)]
    except:
        courses = [course_raw] if course_raw else []
    
    course_str = f"\n🎓 *Deine Kurse:* {', '.join([f'`{c}`' for c in courses])}" if courses else "\n🎓 *Deine Kurse:* Noch keine (nutze /setcourse)"
    
    await update.message.reply_text(
        f"📊 *Deine Statistik*{course_str}\n"
        f"Anfragen letzte Stunde: `{recent}/{limit if limit else '∞'}`\n"
        f"Noch verfügbar: `{remaining}`\nGesamt: `{total}` Anfragen\n"
        f"Tokens: `{tok_in + tok_out:,}`\nGesprächsverlauf: `{history_len} Austausch(e)`",
        parse_mode="Markdown"
    )


async def cmd_setcourse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Interaktiver Assistent zum Festlegen des eigenen Studiengangs (Multi-Select)."""
    if not _personal_features[0]:
        await update.message.reply_text("💡 Dieses Feature ist aktuell deaktiviert.")
        return
    await _show_faculty_selection(update.message.reply_text)


async def _show_faculty_selection(reply_func, text_prefix=""):
    try:
        faculties = await raumzeit.get_departments()
        keyboard = []
        for f in faculties:
            name = f.get("name") or f.get("shortName", "Unknown")
            keyboard.append([InlineKeyboardButton(name, callback_data=f"setc_fac:{f['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ Abbrechen / Beenden", callback_data="setc_abort")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_func(
            f"{text_prefix}*Schritt 1 von 3:* Wähle eine Fakultät zum Hinzufügen:", 
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await reply_func(f"⚠️ Fehler: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet die Klicks auf die Inline-Buttons des setcourse-Assistenten."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id

    if data == "setc_abort":
        await query.edit_message_text("✅ Vorgang beendet. Deine bisherigen Einstellungen (falls vorhanden) bleiben gespeichert.")
        return

    if not _personal_features[0]:
        await query.edit_message_text("💡 Dieses Feature wurde deaktiviert.")
        return

    if data.startswith("setc_fac:"):
        fac_id = data.split(":")[1]
        try:
            courses = await raumzeit.get_courses_of_study(fac_id)
            keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"setc_deg:{c['name']}")] for c in courses]
            keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="setc_more")])
            await query.edit_message_text(
                "*Schritt 2 von 3:* Wähle deinen Studiengang:", 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"⚠️ Fehler: {e}")

    elif data.startswith("setc_deg:"):
        deg_abbr = data.split(":")[1]
        keyboard = []
        for i in range(1, 8, 2):
            row = [InlineKeyboardButton(f"Sem. {i}", callback_data=f"setc_add:{deg_abbr}.{i}")]
            if i + 1 <= 7:
                row.append(InlineKeyboardButton(f"Sem. {i+1}", callback_data=f"setc_add:{deg_abbr}.{i+1}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Zurück zur Fakultät", callback_data="setc_more")])
        await query.edit_message_text(
            f"*Schritt 3 von 3:* Welches Semester für *{deg_abbr}*?", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("setc_add:"):
        full_key = data.split(":")[1]
        await db.add_primary_course(user_id, full_key)
        u = await db.get_user(user_id)
        import json
        try:
            courses = json.loads(u["primary_course"]) if u["primary_course"] else []
            if not isinstance(courses, list): courses = [str(courses)]
        except:
            courses = [u["primary_course"]] if u["primary_course"] else []
        
        course_list = ", ".join(f"`{c}`" for c in courses)
        keyboard = [
            [InlineKeyboardButton("➕ Weiteres Semester hinzufügen", callback_data="setc_more")],
            [InlineKeyboardButton("✅ Fertig & Speichern", callback_data="setc_done")],
            [InlineKeyboardButton("🗑 Alle löschen & neu starten", callback_data="setc_clear")]
        ]
        await query.edit_message_text(
            f"✨ *Stundenplan konfiguriert*\n\nAktuell ausgewählt: {course_list}\n\nMöchtest du noch ein Semester hinzufügen oder bist du fertig?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "setc_more":
        await _show_faculty_selection(query.edit_message_text)
    
    elif data == "setc_done":
        await query.edit_message_text("✅ Deine Einstellungen wurden gespeichert. Du kannst mich nun jederzeit fragen: 'Was habe ich heute?'.")

    elif data == "setc_clear":
        await db.set_primary_courses(user_id, [])
        await _show_faculty_selection(query.edit_message_text, "🗑 Liste geleert.\n\n")

    elif data.startswith("err_save:"):
        if not admin._is_admin(user_id):
            await query.answer("⛔ Nur für Admins.")
            return
        
        err_id = data.split(":")[1]
        err_data = _error_cache.get(err_id)
        if not err_data:
            await query.edit_message_text("⚠️ Fehlerdaten nicht mehr im Cache (Bot-Neustart?).")
            return
            
        filename = admin.save_issue_from_log(err_data)
        await query.edit_message_text(f"✅ Issue erstellt: `issues/active/{filename}`", parse_mode="Markdown")
        # Aus Cache entfernen um Speicher zu sparen
        _error_cache.pop(err_id, None)


async def cmd_myplan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt den personalisierten Wochenstundenplan."""
    from src.state import _personal_features
    if not _personal_features[0]:
        await update.message.reply_text("💡 Dieses Feature ist aktuell deaktiviert.")
        return
        
    user_id = update.effective_user.id
    u = await db.get_user(user_id)
    raw = u.get("primary_course") if u else None
    
    try:
        courses = json.loads(raw) if raw else []
        if not isinstance(courses, list): courses = [str(raw)]
    except:
        courses = [raw] if raw else []
        
    if not courses or not courses[0]:
        await update.message.reply_text("🎓 Du hast noch keine Kurse hinterlegt. Nutze /setcourse um dies zu tun.")
        return

    # Check Cache
    cached = await db.get_user_plan_cache(user_id)
    if cached:
        day_msgs = formatter.format_weekly_plan(cached.get("bookings", []))
        for msg in day_msgs:
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except:
                await update.message.reply_text(msg)
        return

    # No Cache -> Fetch from API
    msg = await update.message.reply_text("🔄 Rufe deinen Stundenplan ab...")
    all_bookings = []
    for course in courses:
        res = await raumzeit.get_course_timetable(course)
        if "bookings" in res:
            all_bookings.extend(res["bookings"])
    
    # Save to Cache
    await db.save_user_plan_cache(user_id, {"bookings": all_bookings})
    
    # Format and Send
    day_msgs = formatter.format_weekly_plan(all_bookings)
    await msg.delete()
    for m in day_msgs:
        try:
            await update.message.reply_text(m, parse_mode="Markdown")
        except:
            await update.message.reply_text(m)


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
        
        # Sonderaktionen prüfen (z.B. Lageplan senden)
        map_sent = False
        if _map_feature[0]:
            for name, res in collected_results:
                if name == "get_campus_map" and res.get("action") == "send_map":
                    building = res.get("building")
                    map_path = f"data/maps/map_{building}.png"
                    import os
                    if os.path.exists(map_path):
                        await context.bot.send_photo(chat_id=chat_id, photo=open(map_path, "rb"), caption=reply, parse_mode="Markdown")
                        map_sent = True
                        break
        
        if not map_sent:
            if CONFIRM_SENTINEL in reply:
                course = next((r.get("course_semester", "") for n, r in collected_results if n == "get_course_timetable"), "")
                queried_date = next((r.get("queried_date") for n, r in collected_results if n == "get_course_timetable"), None)
                raw_date = queried_date if (queried_date and len(queried_date) == 10) else None
                _pending_confirmation[chat_id] = (text, course, 1, raw_date)
            await _send_reply(update, chat_id, reply)
    except Exception as exc:
        log.exception("Agent-Fehler"); await update.message.reply_text(f"⚠️ Fehler: {exc}")

async def _send_reply(update, chat_id: int, reply: str) -> None:
    # Telegram Limit ist 4096 Zeichen. Wir nutzen 4000 zur Sicherheit.
    MAX_LEN = 4000
    
    if len(reply) <= MAX_LEN:
        try:
            msg = await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            msg = await update.message.reply_text(reply)
        _bot_messages.setdefault(chat_id, []).append(msg.message_id)
        return

    # Nachricht splitten
    chunks = []
    current_chunk = []
    current_len = 0
    
    for line in reply.splitlines(keepends=True):
        if current_len + len(line) > MAX_LEN:
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            # Falls eine einzelne Zeile bereits zu lang ist
            if len(line) > MAX_LEN:
                for i in range(0, len(line), MAX_LEN):
                    chunks.append(line[i:i+MAX_LEN])
                continue
        
        current_chunk.append(line)
        current_len += len(line)
        
    if current_chunk:
        chunks.append("".join(current_chunk))

    for i, chunk in enumerate(chunks):
        suffix = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
        try:
            msg = await update.message.reply_text(chunk + suffix, parse_mode="Markdown")
        except Exception:
            msg = await update.message.reply_text(chunk + suffix)
        _bot_messages.setdefault(chat_id, []).append(msg.message_id)

async def _run_index_build():
    try: n = await raumzeit.build_course_index(); log.info("Kurs-Index: %d Einträge", n)
    except: log.exception("Kurs-Index failed")

async def _run_lecturer_build():
    try: n = await raumzeit.build_lecturer_index(); log.info("Dozenten-Index: %d Matches", n)
    except: log.exception("Dozenten-Index failed")

async def _weekly_lecturer_refresh():
    while True: await asyncio.sleep(7*24*3600); await _run_lecturer_build()

async def _background_sync_scheduler():
    """Führt jede Nacht um 04:00 Uhr einen Sync aus."""
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), _time(4, 0))
        if target <= now:
            target += timedelta(days=1)
        
        wait_seconds = (target - now).total_seconds()
        log.info("Nächster automatischer Sync um 04:00 Uhr (in %.1f Stunden)", wait_seconds / 3600)
        await asyncio.sleep(wait_seconds)
        
        log.info("Starte nächtlichen automatischen Sync...")
        await _run_index_build()
        await _run_lecturer_build()

async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loggt Fehler und beendet den Prozess bei zu vielen Netzwerkfehlern."""
    global _consecutive_network_errors
    if isinstance(context.error, NetworkError):
        _consecutive_network_errors += 1
        log.warning("Telegram Netzwerkfehler (%d/%d): %s", 
                    _consecutive_network_errors, NETWORK_ERROR_THRESHOLD, context.error)
        if _consecutive_network_errors >= NETWORK_ERROR_THRESHOLD:
            log.critical("Zu viele Netzwerkfehler. Beende Bot für Systemd-Restart...")
            os._exit(1) # Harter Exit für sofortigen Restart
    else:
        _consecutive_network_errors = 0
        error_msg = str(context.error)
        tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        
        # Loggen (immer)
        log.error("Unbehandelter Fehler in Bot-Logik: %s (Details in logs/bot.txt)", error_msg, exc_info=False)
        
        # Admins benachrichtigen & Cache befüllen
        err_id = str(uuid.uuid4())[:8]
        user_input = "N/A"
        user_info = "System"
        
        if update and update.effective_user:
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else str(update.effective_user.id)
            if update.effective_message and update.effective_message.text:
                user_input = update.effective_message.text
                
        _error_cache[err_id] = {
            "error": error_msg,
            "traceback": tb,
            "user_input": user_input,
            "user_info": user_info,
            "timestamp": datetime.now().isoformat()
        }
        
        # Benachrichtigung an Admins
        for aid in settings.admin_ids:
            try:
                keyboard = [[InlineKeyboardButton("📝 Issue erstellen", callback_data=f"err_save:{err_id}")]]
                await context.bot.send_message(
                    chat_id=aid,
                    text=f"🚨 *Bot-Fehler*\nUser: {user_info}\nInput: `{user_input}`\n\nError: `{error_msg}`",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            except Exception as e:
                log.warning("Konnte Admin %s nicht über Fehler benachrichtigen: %s", aid, e)

async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    for aid in settings.admin_ids:
        try: await app.bot.set_my_commands(_ADMIN_COMMANDS, scope={"type": "chat", "chat_id": aid})
        except: pass
    if await db.course_index_stale(): asyncio.create_task(_run_index_build())
    if raumzeit.lecturers_stale(): asyncio.create_task(_run_lecturer_build())
    else: raumzeit.load_lecturers()
    
    # Hintergrund-Tasks starten
    asyncio.create_task(_weekly_lecturer_refresh())
    asyncio.create_task(_background_sync_scheduler())

async def main_async() -> None:
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("setcourse", cmd_setcourse))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("myplan", cmd_myplan))
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
    app.add_handler(CommandHandler("togglemap", admin.cmd_togglemap))
    app.add_handler(CommandHandler("maintenance", admin.cmd_maintenance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)

    await app.initialize(); await app.start(); await app.updater.start_polling()
    
    if not IS_DAEMON:
        # Dashboard nur im interaktiven Modus
        terminal.console.print(terminal.make_dashboard())
        stop_event = asyncio.Event()
        await terminal.terminal_loop(app, stop_event)
    else:
        log.info("Bot läuft im Daemon-Modus (Hintergrund).")
        # Im Daemon-Modus einfach unendlich warten
        while True:
            await asyncio.sleep(3600)
    
    await app.updater.stop(); await app.stop(); await app.shutdown()

def main():
    try: asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit): pass

if __name__ == "__main__": main()

