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
import httpx
from datetime import datetime, timedelta, time as _time
from logging.handlers import RotatingFileHandler

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.helpers import escape_markdown

from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db
from src import formatter
from src import admin
from src import terminal
from src import privacy
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
_bug_reports: dict[int, dict] = {} # user_id -> {state, title, context, comment}
_pending_messages: dict[int, str] = {}

_NEIN = {"nein", "ne", "n", "no", "falsch", "stimmt nicht", "stimmt nicht so", "nope"}
_JA   = {"ja", "j", "yes", "y", "stimmt", "korrekt", "ok", "okay"}
_USER_COMMANDS = [
    BotCommand("start", "Erste Schritte & Beispiele"),
    BotCommand("help", "Alle Befehle & Hilfe"),
    BotCommand("privacy", "Datenschutz & DSGVO"),
    BotCommand("consent", "Privacy-Einstellungen"),
    BotCommand("data", "Deine Daten (DSGVO)"),
    BotCommand("export", "Daten-Export (JSON)"),
    BotCommand("delete", "Alle Daten löschen"),
    BotCommand("setcourse", "Studiengang & Filter einstellen"),
    BotCommand("myplan", "Dein persönlicher Stundenplan"),
    BotCommand("mensa", "Speiseplan der Mensa Moltke"),
    BotCommand("stats", "Dein Profil & Token-Verbrauch"),
    BotCommand("bug", "Fehler melden / Feedback geben"),
    BotCommand("reset", "KI-Gedächtnis löschen"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("admin", "System- & Nutzerübersicht"),
    BotCommand("sync", "Datenbank-Abgleich mit HKA"),
    BotCommand("approve", "Nutzer als HKA-Mitglied freischalten"),
    BotCommand("revoke", "HKA-Zugang entziehen"),
    BotCommand("togglepersonal", "Feature: Personalisierung umschalten"),
    BotCommand("togglemap", "Feature: Lageplan umschalten"),
    BotCommand("loglevel", "Logging-Detailtiefe ändern"),
    BotCommand("maintenance", "Wartungsmodus steuern"),
    BotCommand("broadcast", "Nachricht an alle Nutzer senden"),
]

def _is_allowed(user_id: int) -> bool:
    return not settings.allowed_ids or user_id in settings.allowed_ids

def build_optin_text() -> str:
    """Erzeugt den Text für die DSGVO-Zustimmung."""
    return (
        "🏫 *Willkommen beim Raumzeit KI-Bot!*\n\n"
        "Damit ich deine Fragen in natürlicher Sprache beantworten kann, muss ich:\n"
        "1. Deine Nachrichten an unsere KI-Anbieter (z.B. Mistral/OpenAI) weiterleiten.\n"
        "2. Einen Chat-Verlauf speichern, damit die KI den Kontext versteht.\n"
        "3. Ein Basis-Profil (Telegram-ID) für Rate-Limiting anlegen.\n\n"
        "Ohne diese Daten kann der Bot nicht funktionieren. Du kannst später Details via `/consent` "
        "anpassen oder via `/delete` alles löschen."
    )

def build_start_text() -> str:
    """Erzeugt den Willkommenstext für /start."""
    return (
        "🏫 *Willkommen beim Raumzeit KI-Bot!*\n\n"
        "Ich helfe dir bei Fragen rund um den Campus, Stundenpläne und die Mensa.\n\n"
        "💡 *Frag mich einfach:*\n"
        "• _\"Wann ist M-102 heute frei?\"_\n"
        "• _\"Stundenplan MABB.2 am Dienstag\"_\n"
        "• _\"Gibt es heute Pizza in der Mensa?\"_\n\n"
        "🚀 *Erste Schritte:*\n"
        "1️⃣ Nutze `/setcourse`, um dein Semester zu hinterlegen.\n"
        "2️⃣ Frag mich: _\"Was habe ich heute?\"_\n\n"
        "Nutze `/help` für die vollständige Befehlsreferenz.\n"
        "📄 [Quellcode (AGPL-3.0)](https://github.com/Bayyo1337/hka-agentic-raumzeit-bot)"
    )

def build_help_text(is_admin: bool) -> str:
    """Erzeugt die vollständige Hilfe-Referenz."""
    from src.state import _personal_features
    
    lines = [
        "📖 *Raumzeit KI-Bot Hilfe*",
        "",
        "Frag mich einfach in natürlicher Sprache. Ich verstehe Fragen zu Räumen, Kursen, Dozenten und der Mensa.",
        "",
        "🔍 *Beispiele:*",
        "• *Räume:* `Wann ist M-102 heute frei?` oder `Wo ist Gebäude E?`",
    ]
    
    if _personal_features[0]:
        lines.append("• *Kurse:* `Stundenplan MABB.3 am Dienstag` oder `Was habe ich morgen?` (erfordert `/setcourse`)")
    else:
        lines.append("• *Kurse:* `Stundenplan MABB.3 am Dienstag` oder `Was wird in M-102 gelehrt?`")
        
    lines += [
        "• *Dozenten:* `Sprechzeiten von Peter Offermann`",
        "• *Mensa:* `Was gibt es heute zu essen?` oder `Allergene im Seelachs`",
        "• *Karten:* `Wo ist LI-146?` (sendet automatisch Lageplan)",
        "",
        "📜 *Basis-Befehle:*",
        "`/help` – Diese Referenz anzeigen",
        "`/mensa` – Heutiger Speiseplan (Moltke)",
        "`/bug` – Fehler melden oder Feedback geben (interaktiv)",
        "`/reset` – Aktuellen Gesprächskontext löschen",
        "`/stats` – Deine Profil-Daten & Kurse",
        "",
        "🔒 *Datenschutz & DSGVO:*",
        "`/privacy` – Datenschutzerklärung anzeigen",
        "`/consent` – Privacy-Einstellungen verwalten (Opt-In/Out)",
        "`/data` – Übersicht deiner gespeicherten Daten",
        "`/export` – Daten-Export als JSON anfordern",
        "`/delete` – Alle deine Daten unwiderruflich löschen",
        "`/retention` – Aufbewahrungsfristen anpassen",
        "",
    ]
    
    if _personal_features[0]:
        lines += [
            "🎓 *Studium & Personalisierung:*",
            "Hinterlege deine Kurse, um Fragen wie _\"Was habe ich heute?\"_ zu nutzen.",
            "`/setcourse` – Wizard starten (Fakultät → Studiengang → Semester)",
            "`/setcourse add [KEY]` – Kurs direkt speichern (z.B. `/setcourse add MABB.3`)",
            "`/setcourse list` – Deine gespeicherten Kurse anzeigen",
            "`/setcourse clear` – Alle gespeicherten Kurse löschen",
            "`/myplan` – Deinen persönlichen Wochenplan anzeigen",
            "",
        ]

    lines += [
        "ℹ️ *Troubleshooting:*",
        "• *Keine Belegungen?* Prüfe, ob der Kurs-Key korrekt ist (z.B. `MABB.3`) oder ob Vorlesungsfreie Zeit ist.",
    ]
    
    if is_admin:
        lines.append("• *Falsche Infos?* Nutze `/sync` (Admins) oder melde es via `/bug`.")
    else:
        lines.append("• *Falsche Infos?* Melde es via `/bug` an das Entwickler-Team.")
    
    lines.append("")

    if is_admin:
        lines += [
            "🔧 *Admin-Bereich:*",
            "`/admin` – System-Dashboard & Nutzer-Statistik",
            "`/sync [all|courses|lecturers]` – Daten manuell abgleichen",
            "`/user [@username|ID]` – Nutzer-Details & HKA-Freischaltung",
            "`/approve [@username|ID]` – Als HKA-Mitglied freischalten (🎓 Dozenten-Zugriff)",
            "`/revoke [@username|ID]` – HKA-Zugang entziehen",
            "`/broadcast [Text]` – Nachricht an alle Nutzer senden",
            "`/loglevel [DEBUG|INFO|WARNING]` – Detailtiefe der Logs ändern",
            "`/maintenance [An|Aus]` – Wartungsmodus (de)aktivieren",
            "`/togglepersonal` – Feature 'Persönlicher Plan' umschalten",
            "`/togglemap` – Feature 'Lagepläne' umschalten",
        ]
    
    return "\n".join(lines)

def _command_help(is_admin: bool) -> str:
    # Legacy wrapper for backward compatibility if needed, though we should move to build_help_text
    return build_help_text(is_admin)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    is_admin = admin._is_admin(update.effective_user.id)
    await update.message.reply_text(build_help_text(is_admin), parse_mode="Markdown", disable_web_page_preview=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(build_start_text(), parse_mode="Markdown", disable_web_page_preview=True)


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
    """Verwaltet die gespeicherten Kurse und Filter."""
    if not _personal_features[0]:
        await update.message.reply_text("💡 Dieses Feature ist aktuell deaktiviert.")
        return
    
    user_id = update.effective_user.id
    
    if context.args:
        sub = context.args[0].lower()
        if sub == "add" and len(context.args) > 1:
            key = context.args[1].upper().replace("_", ".")
            await db.add_course_to_config(user_id, key)
            await update.message.reply_text(f"✅ Kurs `{key}` hinzugefügt.")
            return
        elif sub == "remove" and len(context.args) > 1:
            key = context.args[1].upper().replace("_", ".")
            await db.remove_course_from_config(user_id, key)
            await update.message.reply_text(f"✅ Kurs `{key}` entfernt.")
            return
        elif sub == "clear":
            await db.save_user_course_config(user_id, [])
            await update.message.reply_text("✅ Alle Kurse gelöscht.")
            return
        elif sub == "list":
            config = await db.get_user_course_config(user_id)
            if not config:
                await update.message.reply_text("🎓 Du hast noch keine Kurse hinterlegt.")
            else:
                lines = ["🎓 *Deine gespeicherten Kurse:*"]
                for c in config:
                    line = f"• `{c['key']}`"
                    if c.get("excluded_modules") or c.get("excluded_groups"):
                        line += " (gefiltert)"
                    lines.append(line)
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return

    await _show_setcourse_menu(update.message.reply_text, user_id)


async def _show_setcourse_menu(reply_func, user_id: int, text_prefix=""):
    config = await db.get_user_course_config(user_id)
    
    lines = [f"{text_prefix}⚙️ *Kurs-Management*", ""]
    if not config:
        lines.append("_Noch keine Kurse hinterlegt._")
    else:
        for c in config:
            line = f"• `{c['key']}`"
            filters = []
            if c.get("excluded_modules"): filters.append(f"{len(c['excluded_modules'])} Module")
            if c.get("excluded_groups"): filters.append(f"{len(c['excluded_groups'])} Gruppen")
            if filters:
                line += " 🛠 " + ", ".join(filters)
            lines.append(line)
    
    lines.append("\nWas möchtest du tun?")
    
    keyboard = [
        [InlineKeyboardButton("➕ Semester hinzufügen", callback_data="setc_more")],
        [InlineKeyboardButton("🛠 Veranstaltungen filtern", callback_data="setc_filter_select")],
        [InlineKeyboardButton("🗑 Semester entfernen", callback_data="setc_rem_select")],
        [InlineKeyboardButton("🧼 Alles löschen", callback_data="setc_clear")],
        [InlineKeyboardButton("✅ Fertig", callback_data="setc_done")]
    ]
    
    await reply_func(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _show_faculty_selection(reply_func, text_prefix=""):
    try:
        faculties = await raumzeit.get_departments()
        # Nur echte Fakultaeten anzeigen (Dezernate etc. ausblenden)
        faculties = [f for f in faculties if f.get("faculty")]
        
        keyboard = []
        for f in faculties:
            # Die API nutzt 'name' als ID (Kürzel)
            fac_id = f.get("name")
            display_name = f.get("longName") or fac_id
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"setc_fac:{fac_id}")])
        
        keyboard.append([InlineKeyboardButton("❌ Abbrechen / Beenden", callback_data="setc_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_func(
            f"{text_prefix}*Schritt 1 von 3:* Wähle eine Fakultät zum Hinzufügen:", 
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await reply_func(f"⚠️ Fehler: {e}")


async def _show_course_filter_options(query, user_id: int, key: str):
    # Wir brauchen die Bookings um zu wissen was es gibt
    res = await raumzeit.get_course_timetable(key)
    bookings = res.get("bookings", [])
    
    modules = sorted(list(set(b.get("name") for b in bookings if b.get("name"))))
    groups = sorted(list(set(b.get("group") for b in bookings if b.get("group"))))
    
    config = await db.get_user_course_config(user_id)
    course_cfg = next((c for c in config if c["key"].upper() == key.upper()), None)
    if not course_cfg:
        await query.edit_message_text("⚠️ Kurs nicht gefunden.")
        return

    excl_m = course_cfg.get("excluded_modules", [])
    excl_g = course_cfg.get("excluded_groups", [])
    
    lines = [f"🛠 *Filter für {key}*", "", "Klicke auf eine Veranstaltung/Gruppe, um sie zu de-/aktivieren. Deaktivierte Elemente werden im Plan ausgeblendet.", ""]
    
    keyboard = []
    
    if groups:
        lines.append("*Gruppen:*")
        for g in groups:
            status = "❌" if g in excl_g else "✅"
            keyboard.append([InlineKeyboardButton(f"{status} Gruppe {g}", callback_data=f"setc_tg:{key}:{g}")])
    
    if modules:
        lines.append("*Module:*")
        for m in modules:
            status = "❌" if m in excl_m else "✅"
            # Text kürzen falls zu lang für Button
            display_m = (m[:35] + '..') if len(m) > 37 else m
            keyboard.append([InlineKeyboardButton(f"{status} {display_m}", callback_data=f"setc_tm:{key}:{m}")])
            
    keyboard.append([InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="setc_main")])
    
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def cmd_bug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Startet den interaktiven Bug-Reporting-Prozess."""
    user_id = update.effective_user.id
    privacy_settings = await db.get_privacy_settings(user_id)
    if not privacy_settings.get("allow_error_reports", False):
        await update.message.reply_text(
            "⚠️ Du hast Fehlerberichte in deinen Datenschutzeinstellungen deaktiviert.\n"
            "Bitte aktiviere 'Fehlerberichte' via /consent, um Feedback zu senden."
        )
        return

    _bug_reports[user_id] = {"state": "WAITING_FOR_TITLE"}
    await update.message.reply_text(
        "📝 *Feedback & Bug-Reporting*\n\n"
        "Schön, dass du helfen möchtest! Bitte gib als Erstes einen **kurzen, aussagekräftigen Titel** für dein Feedback ein:",
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet die Klicks auf die Inline-Buttons des setcourses-Assistenten."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id

    if data == "privacy_opt_in_details":
        await query.edit_message_text(
            "Alle Informationen zum Datenschutz findest du hier:\n\n"
            "Nutze den Befehl `/privacy`, um die Details direkt im Chat zu lesen, oder besuche "
            "[GitHub](https://github.com/Bayyo1337/hka-agentic-raumzeit-bot/blob/gemini/docs/DSGVO.md).\n\n"
            "Bist du mit der Verarbeitung einverstanden?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Ich stimme zu", callback_data="privacy_opt_in")]]),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    if data == "privacy_opt_in":
        await db.set_consent_status(user_id, 1)
        pending_msg = _pending_messages.pop(user_id, "")
        await query.edit_message_text("✅ Danke für deine Zustimmung! Ich verarbeite nun deine erste Anfrage...")
        
        user = update.effective_user
        privacy_settings = await db.get_privacy_settings(user_id)
        if privacy_settings.get("allow_profile", True):
            await db.upsert_user(user_id, user.username or "", user.first_name or "")

        if pending_msg:
            chat_id = update.effective_chat.id
            asyncio.create_task(_process_user_message(update, context, chat_id, user_id, user, pending_msg, privacy_settings))
        return

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
            # Auch hier: 'name' ist die ID
            keyboard = [[InlineKeyboardButton(c["longName"], callback_data=f"setc_deg:{c['name']}")] for c in courses]
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
        
        # Prüfung auf Varianten (Gruppen)
        parts = full_key.split(".")
        if len(parts) == 2:
            abbr, sem = parts
            variants = await db.get_course_variants(abbr, int(sem))
            if len(variants) > 1:
                # Mehrere Varianten -> Auswahl zeigen
                keyboard = []
                for v in variants:
                    # v ist der volle Key, z.B. MABB.3.E
                    label = v.split(".")[-1] if "." in v else v
                    keyboard.append([InlineKeyboardButton(f"Gruppe {label}", callback_data=f"setc_addv:{v}")])
                keyboard.append([InlineKeyboardButton("Nur Basis-Kurs (nicht empfohlen)", callback_data=f"setc_addv:{full_key}")])
                keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="setc_more")])
                
                await query.edit_message_text(
                    f"Für *{full_key}* wurden verschiedene Gruppen gefunden.\nWelcher Gruppe gehörst du an?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
                return
            elif len(variants) == 1:
                # Nur eine Variante -> Direkt diese nehmen
                full_key = variants[0]

        await db.add_course_to_config(user_id, full_key)
        await _show_setcourse_menu(query.edit_message_text, user_id, f"✅ Kurs `{full_key}` hinzugefügt.\n\n")

    elif data.startswith("setc_addv:"):
        full_key = data.split(":")[1]
        await db.add_course_to_config(user_id, full_key)
        await _show_setcourse_menu(query.edit_message_text, user_id, f"✅ Kurs `{full_key}` hinzugefügt.\n\n")

    elif data == "setc_more":
        await _show_faculty_selection(query.edit_message_text)
    
    elif data == "setc_done":
        await query.edit_message_text("✅ Deine Einstellungen wurden gespeichert. Du kannst mich nun jederzeit fragen: 'Was habe ich heute?'.")

    elif data == "setc_clear":
        await db.save_user_course_config(user_id, [])
        await _show_setcourse_menu(query.edit_message_text, user_id, "🧼 Alle Kurse gelöscht.\n\n")

    elif data == "setc_rem_select":
        config = await db.get_user_course_config(user_id)
        if not config:
            await query.answer("Keine Kurse zum Entfernen.")
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {c['key']}", callback_data=f"setc_rem_course:{c['key']}")] for c in config]
        keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="setc_main")])
        await query.edit_message_text("Welchen Kurs möchtest du entfernen?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("setc_rem_course:"):
        key = data.split(":")[1]
        await db.remove_course_from_config(user_id, key)
        await _show_setcourse_menu(query.edit_message_text, user_id, f"✅ Kurs `{key}` entfernt.\n\n")

    elif data == "setc_filter_select":
        config = await db.get_user_course_config(user_id)
        if not config:
            await query.answer("Zuerst einen Kurs hinzufügen!")
            return
        keyboard = [[InlineKeyboardButton(f"🛠 {c['key']}", callback_data=f"setc_filter_course:{c['key']}")] for c in config]
        keyboard.append([InlineKeyboardButton("⬅️ Zurück", callback_data="setc_main")])
        await query.edit_message_text("Für welchen Kurs möchtest du Veranstaltungen filtern?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("setc_filter_course:"):
        key = data.split(":")[1]
        await _show_course_filter_options(query, user_id, key)

    elif data.startswith("setc_tg:") or data.startswith("setc_tm:"):
        parts = data.split(":")
        mode = parts[0]
        key = parts[1]
        val = parts[2]
        
        config = await db.get_user_course_config(user_id)
        for c in config:
            if c["key"].upper() == key.upper():
                if mode == "setc_tg":
                    excl = c.setdefault("excluded_groups", [])
                    if val in excl: excl.remove(val)
                    else: excl.append(val)
                else:
                    excl = c.setdefault("excluded_modules", [])
                    if val in excl: excl.remove(val)
                    else: excl.append(val)
                break
        await db.save_user_course_config(user_id, config)
        await _show_course_filter_options(query, user_id, key)

    elif data == "setc_main":
        await _show_setcourse_menu(query.edit_message_text, user_id)

    elif data.startswith("err_save:"):
        if not admin._is_admin(user_id):
            await query.answer("⛔ Nur für Admins.")
            return
        
        err_id = data.split(":")[1]
        err_data = _error_cache.get(err_id)
        if not err_data:
            await query.edit_message_text("⚠️ Fehlerdaten nicht mehr im Cache (Bot-Neustart?).")
            return
            
        filename = await admin.save_issue_from_log(err_data)
        await query.edit_message_text(f"✅ Feedback gespeichert: `{filename}`", parse_mode="Markdown")
        # Aus Cache entfernen um Speicher zu sparen
        _error_cache.pop(err_id, None)

    elif data.startswith("bug_ctx:") or data == "bug_no_ctx":
        ctx_val = "Kein Kontext" if data == "bug_no_ctx" else data.split(":", 1)[1]
        _bug_reports[user_id]["context"] = ctx_val
        _bug_reports[user_id]["state"] = "WAITING_FOR_COMMENT"
        await query.edit_message_text(
            f"✅ Kontext gespeichert: `{ctx_val}`\n\nBitte beschreibe nun dein Anliegen so detailliert wie möglich (Zusatztext):",
            parse_mode="Markdown"
        )

    elif data.startswith("hka_approve:") or data.startswith("hka_revoke:"):
        if not admin._is_admin(user_id):
            await query.answer("⛔ Nur für Admins.")
            return
        action, target_str = data.split(":", 1)
        try:
            target_uid = int(target_str)
        except ValueError:
            await query.answer("❌ Ungültige User-ID.")
            return
        is_approve = action == "hka_approve"
        await db.set_hka_member(target_uid, is_approve)
        status = "🎓 HKA-Zugang freigeschalten" if is_approve else "👤 HKA-Zugang entzogen"
        await query.answer(status)
        text, keyboard = await admin.build_user_detail(target_uid)
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            pass


async def cmd_mensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shortcut-Befehl für den heutigen Mensa-Speiseplan."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id): return
    
    msg = await update.message.reply_text("🔄 Rufe Speiseplan ab...")
    try:
        # Default: Moltke, Heute
        result = await raumzeit.get_mensa_menu()
        reply = formatter.format_results([("get_mensa_menu", result)], "/mensa")
        await msg.edit_text(reply, parse_mode="Markdown")
    except Exception as exc:
        log.exception("Fehler in cmd_mensa")
        await msg.edit_text(f"⚠️ Fehler beim Abrufen des Speiseplans: {exc}")


async def cmd_myplan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt den personalisierten Wochenstundenplan."""
    from src.state import _personal_features
    if not _personal_features[0]:
        await update.message.reply_text("💡 Dieses Feature ist aktuell deaktiviert.")
        return
        
    user_id = update.effective_user.id
    config = await db.get_user_course_config(user_id)
        
    if not config:
        await update.message.reply_text("🎓 Du hast noch keine Kurse hinterlegt. Nutze /setcourse um dies zu tun.")
        return

    # Check Cache
    cached = await db.get_user_plan_cache(user_id)
    if cached:
        day_msgs = formatter.format_weekly_plan(cached.get("bookings", []), user_config=config)
        for msg in day_msgs:
            try:
                await update.message.reply_text(msg, parse_mode="Markdown")
            except:
                await update.message.reply_text(msg)
        return

    # No Cache -> Fetch from API
    msg = await update.message.reply_text("🔄 Rufe deinen Stundenplan ab...")
    all_bookings = []
    for c in config:
        res = await raumzeit.get_course_timetable(c["key"])
        if "bookings" in res:
            all_bookings.extend(res["bookings"])
    
    # Save to Cache
    await db.save_user_plan_cache(user_id, {"bookings": all_bookings})
    
    # Format and Send
    day_msgs = formatter.format_weekly_plan(all_bookings, user_config=config)
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

    privacy_settings = await db.get_privacy_settings(user_id)
    has_consented = await db.get_consent_status(user_id)

    if has_consented == 0:
        await db.upsert_user(user_id, "", "")
    elif privacy_settings.get("allow_profile", True):
        await db.upsert_user(user_id, user.username or "", user.first_name or "")

    if not admin._is_admin(user_id) and await db.is_banned(user_id):
        await update.message.reply_text("⛔ Du wurdest gesperrt.")
        return

    if has_consented == 0:
        _pending_messages[user_id] = text
        keyboard = [
            [InlineKeyboardButton("✅ Ich stimme zu", callback_data="privacy_opt_in")],
            [InlineKeyboardButton("📄 Details lesen", callback_data="privacy_opt_in_details")]
        ]
        await update.message.reply_text(
            build_optin_text(),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    await _process_user_message(update, context, chat_id, user_id, user, text, privacy_settings)

async def _process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, user, text: str, privacy_settings: dict | None = None) -> None:
    if privacy_settings is None:
        privacy_settings = await db.get_privacy_settings(user_id)

    if _maintenance[0] and not admin._is_admin(user_id):
        await update.effective_message.reply_text(_maintenance[1])
        return

    custom_limit = await db.get_custom_rate_limit(user_id)
    limit = custom_limit if custom_limit >= 0 else settings.rate_limit_per_hour
    if not await db.check_rate_limit(user_id, limit):
        await update.effective_message.reply_text(f"⏳ Du hast das Limit von {limit} Anfragen/Stunde erreicht.")
        return

    # Bug-Reporting Workflow
    if user_id in _bug_reports:
        report = _bug_reports[user_id]
        state = report.get("state")
        
        if state == "WAITING_FOR_TITLE":
            report["title"] = text
            report["state"] = "WAITING_FOR_CONTEXT"
            # Letzte Befehle aus Historie holen
            history = await db.load_history(chat_id)
            user_cmds = list(dict.fromkeys([m["content"] for m in history if m["role"] == "user"])) # Deduplizieren
            
            keyboard = []
            for cmd in user_cmds[-5:]: # Letzte 5
                keyboard.append([InlineKeyboardButton(f"💬 {cmd[:30]}...", callback_data=f"bug_ctx:{cmd[:50]}")])
            keyboard.append([InlineKeyboardButton("⏭ Kein Kontext", callback_data="bug_no_ctx")])
            
            await update.effective_message.reply_text(
                f"Titel: *{text}*\n\n*Schritt 2:* Welcher deiner letzten Befehle gehört zu diesem Problem?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
            
        elif state == "WAITING_FOR_COMMENT":
            user_info = f"@{user.username}" if user.username else str(user_id)
            filename = await admin.save_user_issue(report["title"], report.get("context", "N/A"), text, user_info)
            _bug_reports.pop(user_id)
            await update.effective_message.reply_text(
                f"✅ *Vielen Dank!*\n\nDein Feedback wurde gespeichert:\n`{filename}`",
                parse_mode="Markdown"
            )
            return

    # Bestätigungsfrage auswerten (Eskalations-Logik)
    if chat_id in _pending_confirmation:
        normalized = text.strip().lower()
        original_query, course_key, stufe, queried_date = _pending_confirmation.pop(chat_id)
        if normalized in _JA:
            await update.effective_message.reply_text("👍 Alles klar.")
            return
        if normalized in _NEIN or stufe >= 2:
            if stufe == 1:
                msg = await update.effective_message.reply_text("🔄 Suche alle Varianten...")
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
                        await update.effective_message.reply_text(f"⚠️ Fehler: {exc}"); return
                    if CONFIRM_SENTINEL in reply: stufe = 3
                    else: await _send_reply(update, chat_id, reply); return
            if stufe >= 3:
                await update.effective_message.reply_text("😕 Keine Daten gefunden. Deine Anfrage wurde für manuelle Prüfung gespeichert.")
                return

    user_label = f"@{user.username}" if user.username else str(user_id)
    redacted_text = privacy.redact_pii(text)
    log.debug("Anfrage von %s (chat=%d): %.80s", user_label, chat_id, redacted_text)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Nutzer-Profil laden (für persönlichen Stundenplan + HKA-Zugriff)
    u = await db.get_user(user_id)
    primary_course = u.get("primary_course") if u else None
    has_raumzeit_access = bool(u.get("is_hka_member")) if u else False

    history = await db.load_history(chat_id)
    try:
        intent = "smalltalk_fallback"
        if settings.router_enabled:
            try:
                from src.router import router_instance
                router_result = await router_instance.classify_message(
                    text, 
                    {"user_id": user_id, "chat_id": chat_id, "primary_course": primary_course}, 
                    u or {}
                )
                log.info("Router Result: Intent=%s, Confidence=%.2f, Strategy=%s",
                         router_result.intent, router_result.confidence, router_result.strategy.action)

                intent = router_result.intent

                if router_result.strategy.action == "ask_clarification":
                    await db.set_intent_state(user_id, router_result.intent, router_result.entities)
                    await _send_reply(update, chat_id, "Es fehlen noch Informationen: " + router_result.strategy.reason)
                    return

            except Exception as router_exc:
                log.warning("Router Failed: %s", router_exc)

        reply, tok_in, tok_out, collected_results = await agent.run(
            text, history, user_id=user_id, user_label=user_label, primary_course=primary_course, intent=intent,
            has_raumzeit_access=has_raumzeit_access
        )
        # Heuristik: Ist es eine persönliche Anfrage?
        is_personal = any(kw in text.lower() for kw in ["mein", "ich", "heute", "morgen", "nächste woche"]) and primary_course is not None

        # Re-format with user config for filtering
        config = await db.get_user_course_config(user_id) if u else []
        reply = formatter.format_results(collected_results, text, user_config=config, is_personal=is_personal)
        
        # Update history with filtered reply
        if history and history[-1]["role"] == "assistant":
            history[-1]["content"] = reply

        if privacy_settings.get("allow_history", True):
            await db.save_history(chat_id, history)
        
        if privacy_settings.get("allow_profile", True):
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
        log.exception("Agent-Fehler"); await update.effective_message.reply_text(f"⚠️ Fehler: {exc}")
        
    if not IS_DAEMON:
        # Den Prompt für den lokalen Konsolennutzer nach den Logs neu zeichnen
        sys.stdout.write("\rraumzeit> ")
        sys.stdout.flush()

async def _send_reply(update, chat_id: int, reply: str) -> None:
    # Telegram Limit ist 4096 Zeichen. Wir nutzen 4000 zur Sicherheit.
    MAX_LEN = 4000
    
    if len(reply) <= MAX_LEN:
        try:
            msg = await update.effective_message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            msg = await update.effective_message.reply_text(reply)
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
            msg = await update.effective_message.reply_text(chunk + suffix, parse_mode="Markdown")
        except Exception:
            msg = await update.effective_message.reply_text(chunk + suffix)
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
    """Führt jede Nacht um 04:00 Uhr einen Sync aus (Kurse & Mensa)."""
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), _time(4, 0))
        if target <= now:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        log.info("Background-Sync geplant in %.1f Stunden.", wait_seconds / 3600)
        await asyncio.sleep(wait_seconds)

        log.info("Starte nächtlichen Background-Sync...")
        await _run_index_build()
        await raumzeit.get_mensa_menu() # Proaktives Caching
        log.info("Nächtlicher Sync abgeschlossen.")

        await _run_lecturer_build()

async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loggt Fehler und beendet den Prozess bei zu vielen Netzwerkfehlern."""
    global _consecutive_network_errors
    
    # Netzwerk-Fehler (Telegram oder Httpx Polling)
    if isinstance(context.error, NetworkError) or isinstance(context.error, httpx.ReadError):
        _consecutive_network_errors += 1
        log.warning("Verbindungsfehler (%d/%d): %s", 
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
        uid = 0
        anonymized = False
        
        # Sicherer Zugriff auf update-Attribute
        if update:
            effective_user = getattr(update, "effective_user", None)
            if effective_user:
                uid = effective_user.id
                user_info = f"@{effective_user.username}" if effective_user.username else str(uid)
            
            effective_message = getattr(update, "effective_message", None)
            if effective_message and effective_message.text:
                user_input = effective_message.text

        # Privacy Check & Redaktion
        report_uid = uid
        user_input = privacy.redact_pii(user_input)
        if uid > 0:
            privacy_settings = await db.get_privacy_settings(uid)
            if not privacy_settings.get("allow_error_reports", False):
                report_uid = 0
                user_input = "[REDACTED]"
                user_info = "Anonymous"
                anonymized = True

        _error_cache[err_id] = {
            "error": error_msg,
            "traceback": tb,
            "user_input": user_input,
            "user_info": user_info,
            "user_id": report_uid, # Für Kompatibilität mit save_issue_from_log
            "report_uid": report_uid,
            "timestamp": datetime.now().isoformat()
        }
        
        # Benachrichtigung an Admins
        status_tag = " (Anonymisiert)" if anonymized else ""
        for aid in settings.admin_ids:
            try:
                keyboard = [[InlineKeyboardButton("📝 Issue erstellen", callback_data=f"err_save:{err_id}")]]
                await context.bot.send_message(
                    chat_id=aid,
                    text=(
                        f"🚨 *Bot-Fehler*{status_tag}\n"
                        f"User: {escape_markdown(user_info)}\n"
                        f"Input: `{escape_markdown(user_input)}`\n\n"
                        f"Error: `{escape_markdown(error_msg)}`"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            except Exception as e:
                log.warning("Konnte Admin %s nicht über Fehler benachrichtigen: %s", aid, e)

async def gdpr_cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """Führt nächtliche DSGVO-Bereinigung durch."""
    try:
        stats = await db.run_gdpr_cleanup()
        log.info("DSGVO-Bereinigung abgeschlossen: %s", stats)
    except Exception as e:
        log.error("Fehler bei DSGVO-Bereinigung: %s", e)

async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    for aid in settings.admin_ids:
        try: await app.bot.set_my_commands(_ADMIN_COMMANDS, scope={"type": "chat", "chat_id": aid})
        except: pass
    if await db.course_index_stale(): asyncio.create_task(_run_index_build())
    if raumzeit.lecturers_stale(): asyncio.create_task(_run_lecturer_build())
    else: raumzeit.load_lecturers()
    
    # Proaktiver Mensa-Sync bei Start
    asyncio.create_task(raumzeit.get_mensa_menu())
    
    # Hintergrund-Tasks starten
    asyncio.create_task(_weekly_lecturer_refresh())
    asyncio.create_task(_background_sync_scheduler())
    
    # DSGVO-Cleanup Job (jeden Tag um 04:30)
    if app.job_queue:
        app.job_queue.run_daily(gdpr_cleanup_job, time=_time(4, 30))

async def main_async() -> None:
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_post_init).build()
    
    # GDPR & Privacy
    privacy.register_handlers(app)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("bug", cmd_bug))
    app.add_handler(CommandHandler("mensa", cmd_mensa))
    app.add_handler(CommandHandler(["setcourse", "setcourses"], cmd_setcourse))
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
    app.add_handler(CommandHandler("approve", admin.cmd_approve))
    app.add_handler(CommandHandler("revoke", admin.cmd_revoke))
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

    # Bot initialisieren mit Retry-Logik für Robustheit bei schlechter Verbindung
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            log.info("Bot erfolgreich gestartet und verbunden.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                log.warning("Fehler beim Bot-Start (Versuch %d/%d): %s. Neustart in %ds...", 
                            attempt + 1, max_retries, e, wait)
                await asyncio.sleep(wait)
            else:
                log.error("Bot-Start nach %d Versuchen endgültig fehlgeschlagen: %s", max_retries, e)
                raise
    
    if not IS_DAEMON:
        # Dashboard nur im interaktiven Modus
        terminal.console.print(terminal.make_dashboard())
        stop_event = asyncio.Event()
        await terminal.terminal_loop(app, stop_event)
    else:
        log.info("Bot läuft im Daemon-Modus (Hintergrund).")
        # Im Daemon-Modus einfach unendlich warten
        while True:
            try:
                await asyncio.sleep(3600)
            except httpx.ReadError:
                # Wird meistens im Polling gefangen, aber falls hier etwas schief geht
                log.warning("Httpx ReadError im Warte-Loop abgefangen.")
    
    # Shutdown-Sequenz mit Logging
    log.debug("Shutdown-Sequenz gestartet...")
    log.debug("Stoppe Telegram-Updater (wartet auf Polling-Timeout)...")
    await app.updater.stop()
    log.debug("Stoppe Application...")
    await app.stop()
    log.debug("Führe Application-Shutdown durch...")
    await app.shutdown()
    log.info("Bot erfolgreich heruntergefahren.")

def main():
    try: asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit): pass

if __name__ == "__main__": main()

