"""
Telegram Bot Entry Point.
Startet den Bot und leitet Nachrichten an den Claude-Agent weiter.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from telegram import Update, BotCommand
from telegram.error import NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db
from src import formatter
from src.formatter import CONFIRM_SENTINEL

# Rich Konfiguration
console = Console()

def set_log_level(level_name: str) -> bool:
    """Ändert das Log-Level aller relevanten Logger zur Laufzeit."""
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        return False
    
    for _name in ("src.bot", "src.agent", "src.tools", "src.db", "src.formatter"):
        logging.getLogger(_name).setLevel(level)
    return True

# Initiales Logging mit Rich
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False)]
)

# Nur eigene Logger auf den konfigurierten Level setzen
set_log_level(settings.log_level)
log = logging.getLogger("src.bot")

_BOT_START = datetime.now()

# Bot-Nachrichten-IDs pro Chat (für /reset → nur aktuelle Session, nicht persistent nötig)
_bot_messages: dict[int, list[int]] = {}

# Offene Bestätigungsfragen: chat_id → (original_query, course_key, stufe, queried_date)
# stufe: 1=Brute-Force, 2=User-Key-Eingabe, 3=aufgeben
_pending_confirmation: dict[int, tuple[str, str, int, str | None]] = {}

_NEIN = {"nein", "ne", "n", "no", "falsch", "stimmt nicht", "stimmt nicht so", "nope"}
_JA   = {"ja", "j", "yes", "y", "stimmt", "korrekt", "ok", "okay"}

# Wartungsmodus: (aktiv, Nachricht)
_maintenance: tuple[bool, str] = (False, "🔧 Der Bot wird gerade gewartet. Bitte versuche es später.")

async def _resolve_target(arg: str) -> int | None:
    """Löst 'user_id', '@username' oder 'username' zu einer user_id auf."""
    arg = arg.strip()
    if arg.lstrip("@").isdigit():
        return int(arg.lstrip("@"))
    user = await db.find_user_by_username(arg)
    return user["user_id"] if user else None


_USER_COMMANDS = [
    BotCommand("start", "Hilfe & Übersicht"),
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
    BotCommand("maintenance", "Wartungsmodus ein-/ausschalten"),
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
            "/ping – API-Erreichbarkeit prüfen",
            "/indexage – Alter des Kurs-Index",
            "/courses <kürzel> – Kurs-Index für Kürzel",
            "/feedback – Feedback-Logs auflisten",
            "/user <id/@name> – Detailansicht",
            "/ban /unban <id/@name> – Nutzer sperren",
            "/resetlimit /cleartokens /clearhistory <id/@name>",
            "/broadcast <text> – An alle Nutzer senden",
            "/setprovider <provider> – LLM wechseln",
            "/maintenance on/off [text] – Wartungsmodus",
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
    global_limit = settings.rate_limit_per_hour

    uptime = now - _BOT_START
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m = rem // 60

    users = await db.get_all_users()
    all_tokens = await db.get_all_tokens()
    index_count = await db.get_course_index_count()
    maint_on, _ = _maintenance

    tok_in_all = sum(v[0] for v in all_tokens.values())
    tok_out_all = sum(v[1] for v in all_tokens.values())
    total_all = sum([await db.get_total_count(u["user_id"]) for u in users])

    provider = agent.current_provider()
    lines = [
        "📋 Admin-Übersicht",
        f"Uptime: {h}h {m}min  |  Provider: {provider}" + (" 🔧 Wartung" if maint_on else ""),
        f"Anfragen gesamt: {total_all}  |  Tokens: {tok_in_all + tok_out_all:,}",
        f"  ↳ Input: {tok_in_all:,}  |  Output: {tok_out_all:,}",
        f"Kurs-Index: {index_count} Einträge  |  Dozenten: {len(raumzeit._LECTURERS)} gematcht",
        "",
    ]

    if not users:
        lines.append("Noch keine Nutzerdaten vorhanden.")
    else:
        lines.append("Nutzer:")
        for u in users:
            uid = u["user_id"]
            name = f"@{u['username']}" if u["username"] else u["first_name"] or str(uid)
            recent = await db.get_recent_count(uid)
            total = await db.get_total_count(uid)
            tok_in, tok_out = all_tokens.get(uid, (0, 0))
            tok = tok_in + tok_out

            effective_limit = u["custom_rate_limit"] if u["custom_rate_limit"] >= 0 else global_limit
            reset_info = ""
            if effective_limit and recent >= effective_limit:
                oldest = await db.get_oldest_recent_ts(uid)
                if oldest:
                    mins = max(0, int((oldest + timedelta(hours=1) - now).total_seconds() / 60))
                    reset_info = f" (reset ~{mins}min)"
            elif effective_limit:
                reset_info = f" ({effective_limit - recent} frei)"

            ban_flag = " 🚫" if u["banned"] else ""
            custom_flag = f" [limit={u['custom_rate_limit']}]" if u["custom_rate_limit"] >= 0 else ""
            lines.append(
                f"👤 {name} ({uid}){ban_flag}{custom_flag}  "
                f"{recent}/{effective_limit if effective_limit else '∞'}/h{reset_info}  |  "
                f"{total} ges.  |  {tok:,} tok"
            )

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
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Prüfe API...")
    result = await raumzeit.ping_api()
    if result.get("ok"):
        text = (
            f"✅ Raumzeit API erreichbar\n"
            f"Auth: {result['auth_ms']}ms  |  API: {result['api_ms']}ms  |  Status: {result['status']}"
        )
    else:
        text = f"❌ Raumzeit API nicht erreichbar\n{result.get('error', '')}"
    await msg.edit_text(text)


@_require_admin
async def cmd_indexage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ts = await db.get_course_index_age()
    count = await db.get_course_index_count()
    lines = ["🗂 Index-Status\n"]
    if ts:
        age = datetime.now() - ts
        h, rem = divmod(int(age.total_seconds()), 3600)
        d, h = divmod(h, 24)
        age_str = (f"{d}d " if d else "") + f"{h}h {rem // 60}min"
        lines.append(f"Kurs-Index: {count} Einträge (vor {age_str})")
    else:
        lines.append("Kurs-Index: leer – /sync ausführen")

    lecturer_count = len(raumzeit._LECTURERS)
    stale = raumzeit.lecturers_stale()
    stale_str = " ⚠️ veraltet" if stale else ""
    lines.append(f"Dozenten-Index: {lecturer_count} gematcht{stale_str}")
    await update.message.reply_text("\n".join(lines))


@_require_admin
async def cmd_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /courses <Kürzel>  z.B. /courses MABB")
        return
    abbr = context.args[0].upper()
    keys = await db.get_course_keys_for_abbr(abbr)
    if not keys:
        await update.message.reply_text(f"Keine Einträge für '{abbr}' im Index. Versuche /sync.")
        return
    await update.message.reply_text(f"🗂 {abbr} ({len(keys)} Einträge):\n" + "\n".join(f"• {k}" for k in keys))


@_require_admin
async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logs = db.list_feedback_logs()
    if not logs:
        await update.message.reply_text("✅ Keine offenen Feedback-Logs.")
        return
    lines = [f"📋 {len(logs)} Feedback-Log(s):"]
    for name in logs:
        lines.append(f"• {name}")
    lines.append("\nMit /delfeedback <dateiname> löschen.")
    await update.message.reply_text("\n".join(lines))


@_require_admin
async def cmd_delfeedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /delfeedback <dateiname>")
        return
    ok = db.delete_feedback_log(context.args[0])
    await update.message.reply_text("✅ Gelöscht." if ok else "❌ Datei nicht gefunden.")


@_require_admin
async def cmd_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /user <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    u = await db.get_user(uid)
    tok_in, tok_out = await db.get_tokens(uid)
    recent = await db.get_recent_count(uid)
    total = await db.get_total_count(uid)
    history = await db.load_history(uid)
    name = f"@{u['username']}" if u and u["username"] else (u["first_name"] if u else str(uid))
    custom_limit = u["custom_rate_limit"] if u else -1
    effective_limit = custom_limit if custom_limit >= 0 else settings.rate_limit_per_hour
    lines = [
        f"👤 {name} (ID: {uid})",
        f"Status: {'🚫 Gesperrt' if u and u['banned'] else '✅ Aktiv'}",
        f"Zuletzt gesehen: {u['last_seen'][:16] if u and u['last_seen'] else 'unbekannt'}",
        f"Rate-Limit: {effective_limit}/h{' (custom)' if custom_limit >= 0 else ''}",
        f"Anfragen: {recent}/h  |  {total} gesamt",
        f"Tokens: {tok_in + tok_out:,} (↑{tok_in:,} / ↓{tok_out:,})",
        f"History-Einträge: {len(history) // 2}",
    ]
    await update.message.reply_text("\n".join(lines))


@_require_admin
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /ban <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    await db.set_banned(uid, True)
    await update.message.reply_text(f"🚫 Nutzer {uid} gesperrt.")


@_require_admin
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /unban <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    await db.set_banned(uid, False)
    await update.message.reply_text(f"✅ Nutzer {uid} entsperrt.")


@_require_admin
async def cmd_resetlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /resetlimit <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    await db.reset_user_requests(uid)
    await update.message.reply_text(f"✅ Rate-Limit-Zähler für {uid} zurückgesetzt.")


@_require_admin
async def cmd_setlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Verwendung: /setlimit <user_id/@name> <limit>  (0 = kein Limit, -1 = global)")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    try:
        limit = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ungültiger Wert. Zahl erwartet.")
        return
    await db.set_custom_rate_limit(uid, limit)
    label = f"{limit}/h" if limit >= 0 else "global"
    await update.message.reply_text(f"✅ Rate-Limit für {uid} auf {label} gesetzt.")


@_require_admin
async def cmd_cleartokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /cleartokens <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    await db.clear_user_tokens(uid)
    await update.message.reply_text(f"✅ Token-Zähler für {uid} zurückgesetzt.")


@_require_admin
async def cmd_clearhistory_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /clearhistory <user_id oder @username>")
        return
    uid = await _resolve_target(context.args[0])
    if uid is None:
        await update.message.reply_text("❌ Nutzer nicht gefunden.")
        return
    await db.clear_history(uid)
    await update.message.reply_text(f"✅ Gesprächsverlauf für {uid} gelöscht.")


@_require_admin
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /broadcast <Nachricht>")
        return
    text = " ".join(context.args)
    users = await db.get_all_users()
    sent, failed = 0, 0
    for u in users:
        if u["banned"]:
            continue
        try:
            await context.bot.send_message(u["user_id"], f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ Gesendet: {sent}  |  Fehler: {failed}")


@_require_admin
async def cmd_setprovider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        from src.agent import _DEFAULTS
        opts = ", ".join(_DEFAULTS.keys())
        await update.message.reply_text(f"Verwendung: /setprovider <provider>\nVerfügbar: {opts}")
        return
    provider = context.args[0].lower()
    ok = agent.set_provider(provider)
    if ok:
        await update.message.reply_text(f"✅ Provider gewechselt zu: {provider}")
    else:
        from src.agent import _DEFAULTS
        opts = ", ".join(_DEFAULTS.keys())
        await update.message.reply_text(f"❌ Unbekannter Provider. Verfügbar: {opts}")


@_require_admin
async def cmd_loglevel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Verwendung: /loglevel <info|debug|warning>")
        return
    level = context.args[0].lower()
    if set_log_level(level):
        await update.message.reply_text(f"✅ Log-Level geändert auf: {level.upper()}")
    else:
        await update.message.reply_text("❌ Ungültiges Level. Erlaubt: info, debug, warning")


@_require_admin
async def cmd_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _maintenance
    if not context.args:
        on, msg = _maintenance
        await update.message.reply_text(
            f"Wartungsmodus: {'AN' if on else 'AUS'}\n"
            f"Verwendung: /maintenance on [Nachricht] | /maintenance off"
        )
        return
    mode = context.args[0].lower()
    if mode == "on":
        custom_msg = " ".join(context.args[1:]) if len(context.args) > 1 else _maintenance[1]
        _maintenance = (True, custom_msg)
        await update.message.reply_text(f"🔧 Wartungsmodus AN\nNachricht: {custom_msg}")
    elif mode == "off":
        _maintenance = (False, _maintenance[1])
        await update.message.reply_text("✅ Wartungsmodus AUS")
    else:
        await update.message.reply_text("Verwendung: /maintenance on [Nachricht] | /maintenance off")


@_require_admin
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Kurs-Index & Dozenten-Index werden neu aufgebaut...")
    try:
        course_count = await raumzeit.build_course_index()
        await msg.edit_text(f"✅ Kurs-Index: {course_count} Einträge\n⏳ Baue Dozenten-Index...")
        lecturer_count = await raumzeit.build_lecturer_index()
        await msg.edit_text(
            f"✅ Kurs-Index: {course_count} Einträge\n"
            f"✅ Dozenten-Index: {lecturer_count} gematcht"
        )
    except Exception as exc:
        log.exception("Index-Aufbau fehlgeschlagen")
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

    # Nutzerdaten speichern / aktualisieren
    await db.upsert_user(user_id, user.username or "", user.first_name or "")

    # Ban-Check
    if not _is_admin(user_id) and await db.is_banned(user_id):
        await update.message.reply_text("⛔ Du wurdest gesperrt. Bitte wende dich an den Admin.")
        return

    # Wartungsmodus
    maint_on, maint_msg = _maintenance
    if maint_on and not _is_admin(user_id):
        await update.message.reply_text(maint_msg)
        return

    # Effektives Rate-Limit (custom oder global)
    custom_limit = await db.get_custom_rate_limit(user_id)
    limit = custom_limit if custom_limit >= 0 else settings.rate_limit_per_hour
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
                if CONFIRM_SENTINEL in reply:
                    # Immer noch leer → Stufe 2
                    reply = reply.replace(
                        CONFIRM_SENTINEL,
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
                    if CONFIRM_SENTINEL in reply:
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
    if CONFIRM_SENTINEL in reply:
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


async def _run_lecturer_build() -> None:
    try:
        count = await raumzeit.build_lecturer_index()
        log.info("Dozenten-Index: Aufbau abgeschlossen, %d Matches", count)
    except Exception:
        log.exception("Dozenten-Index: Aufbau fehlgeschlagen")


async def _weekly_lecturer_refresh() -> None:
    """Erneuert den Dozenten-Index jede Woche im Hintergrund."""
    WEEK = 7 * 24 * 3600
    while True:
        await asyncio.sleep(WEEK)
        log.info("Dozenten-Index: wöchentliche Aktualisierung gestartet")
        await _run_lecturer_build()


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, NetworkError):
        log.debug("Telegram NetworkError (wird automatisch wiederholt): %s", context.error)
    else:
        log.exception("Unbehandelter Fehler", exc_info=context.error)


async def _post_init(app) -> None:
    await db.init()
    await app.bot.set_my_commands(_USER_COMMANDS)
    for admin_id in settings.admin_ids:
        try:
            await app.bot.set_my_commands(
                _ADMIN_COMMANDS,
                scope={"type": "chat", "chat_id": admin_id},
            )
        except Exception:
            pass
    log.info("Bot-Commands registriert, DB bereit")

    if await db.course_index_stale():
        log.info("Kurs-Index: veraltet oder leer – starte Aufbau im Hintergrund")
        asyncio.create_task(_run_index_build())
    else:
        count = await db.get_course_index_count()
        log.info("Kurs-Index: %d Einträge im Cache", count)

    if raumzeit.lecturers_stale():
        log.info("Dozenten-Index: veraltet oder leer – starte Aufbau im Hintergrund")
        asyncio.create_task(_run_lecturer_build())
    else:
        n = raumzeit.load_lecturers()
        log.info("Dozenten-Index: %d Einträge geladen", n)
    asyncio.create_task(_weekly_lecturer_refresh())


def make_dashboard() -> Panel:
    """Erstellt das Status-Panel für das Terminal."""
    table = Table.grid(expand=True)
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")

    uptime = datetime.now() - _BOT_START
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    
    current_llm = agent.current_provider()
    level_int = logging.getLogger("src.bot").getEffectiveLevel()
    level_name = logging.getLevelName(level_int)
    
    table.add_row("Uptime: ", f"{h}h {m}min {s}s")
    table.add_row("LLM: ", f"[bold green]{current_llm}[/bold green]")
    table.add_row("Logs: ", f"[bold yellow]{level_name}[/bold yellow]")
    table.add_row("Status: ", "Bereit für Anfragen" if not _maintenance[0] else "[bold red]Wartung[/bold red]")
    
    return Panel(table, title="[bold blue]Raumzeit Bot Dashboard[/bold blue]", border_style="blue")


# Dashboard Live-Loop
async def dashboard_task(live: Live):
    """Aktualisiert das Dashboard jede Sekunde."""
    while True:
        live.update(make_dashboard())
        await asyncio.sleep(1)


async def terminal_loop(app, stop_event: asyncio.Event):
    """Schleife für Konsolenbefehle."""
    while not stop_event.is_set():
        try:
            # Nutze to_thread für blockierende Eingabe
            cmd_line = await asyncio.to_thread(input, "raumzeit> ")
            if not cmd_line.strip():
                continue
            
            parts = cmd_line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == "exit":
                log.info("Fahre Bot herunter...")
                stop_event.set()
                break
            elif cmd == "status":
                console.print(make_dashboard())
            elif cmd == "loglevel":
                if args:
                    if set_log_level(args[0]):
                        log.info("Loglevel auf %s gesetzt", args[0].upper())
                    else:
                        console.print(f"[red]Ungültiges Loglevel: {args[0]}[/red]. Erlaubt: debug, info, warning, error")
                else:
                    console.print("[yellow]Verwendung:[/yellow] loglevel <debug|info|warning|error>")
            elif cmd == "sync":
                asyncio.create_task(_run_index_build())
                asyncio.create_task(_run_lecturer_build())
            elif cmd == "help":
                console.print("\n[bold cyan]Verfügbare Konsolenbefehle:[/bold cyan]")
                console.print("  [bold green]status[/bold green]          - Zeigt das aktuelle Bot-Dashboard an")
                console.print("  [bold green]loglevel <level>[/bold green] - Ändert die Detailtiefe der Logs (debug, info, warning, error)")
                console.print("  [bold green]sync[/bold green]            - Startet den Neuaufbau der Kurs- und Dozenten-Indizes")
                console.print("  [bold green]help[/bold green]            - Zeigt diese Hilfe an")
                console.print("  [bold green]exit[/bold green]            - Beendet den Bot sicher\n")
            else:
                console.print(f"[red]Unbekannter Befehl: {cmd}[/red]. Nutze 'help'.")
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            break
        except Exception as e:
            log.error("Fehler in Konsole: %s", e)


async def main_async() -> None:
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stats", cmd_stats))
    # Admin commands
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("rooms", cmd_rooms))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("indexage", cmd_indexage))
    app.add_handler(CommandHandler("courses", cmd_courses))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("delfeedback", cmd_delfeedback))
    app.add_handler(CommandHandler("user", cmd_user))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("resetlimit", cmd_resetlimit))
    app.add_handler(CommandHandler("setlimit", cmd_setlimit))
    app.add_handler(CommandHandler("cleartokens", cmd_cleartokens))
    app.add_handler(CommandHandler("clearhistory", cmd_clearhistory_admin))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("setprovider", cmd_setprovider))
    app.add_handler(CommandHandler("loglevel", cmd_loglevel))
    app.add_handler(CommandHandler("maintenance", cmd_maintenance))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(_error_handler)

    stop_event = asyncio.Event()

    # Bot initialisieren & starten
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Live Dashboard & Konsole starten
    with Live(make_dashboard(), console=console, refresh_per_second=1) as live:
        # Task für Live-Update
        _live_task = asyncio.create_task(dashboard_task(live))
        # Task für Terminal-Input
        await terminal_loop(app, stop_event)
        _live_task.cancel()

    # Sauberer Shutdown
    log.info("Beende alle Prozesse...")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


def main() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
