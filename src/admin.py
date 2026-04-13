"""
Admin-Kommando-Handler für den Telegram-Bot.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db
from src import formatter

log = logging.getLogger(__name__)

def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def _require_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Kein Zugriff.")
            return
        return await func(update, context)
    return wrapper


async def _resolve_target(arg: str) -> int | None:
    """Löst 'user_id', '@username' oder 'username' zu einer user_id auf."""
    arg = arg.strip()
    if arg.lstrip("@").isdigit():
        return int(arg.lstrip("@"))
    user = await db.find_user_by_username(arg)
    return user["user_id"] if user else None


@_require_admin
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.state import _BOT_START, _maintenance
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
        dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
        age = datetime.now() - dt
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
    from src.bot import set_log_level
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
    import src.bot
    if not context.args:
        on, msg = src.bot._maintenance
        await update.message.reply_text(
            f"Wartungsmodus: {'AN' if on else 'AUS'}\n"
            f"Verwendung: /maintenance on [Nachricht] | /maintenance off"
        )
        return
    mode = context.args[0].lower()
    if mode == "on":
        custom_msg = " ".join(context.args[1:]) if len(context.args) > 1 else src.bot._maintenance[1]
        src.bot._maintenance = (True, custom_msg)
        await update.message.reply_text(f"🔧 Wartungsmodus AN\nNachricht: {custom_msg}")
    elif mode == "off":
        src.bot._maintenance = (False, src.bot._maintenance[1])
        await update.message.reply_text("✅ Wartungsmodus AUS")
    else:
        await update.message.reply_text("Verwendung: /maintenance on [Nachricht] | /maintenance off")


@_require_admin
async def cmd_togglepersonal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.state import _personal_features
    _personal_features[0] = not _personal_features[0]
    status = "AN" if _personal_features[0] else "AUS"
    await update.message.reply_text(f"✨ Personalisierung (/setcourse) ist jetzt {status}.")


@_require_admin
async def cmd_togglemap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.state import _map_feature
    _map_feature[0] = not _map_feature[0]
    status = "AN" if _map_feature[0] else "AUS"
    await update.message.reply_text(f"📍 Lageplan-Feature (Karten-Anzeige) ist jetzt {status}.")


@_require_admin
async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.bot import _run_index_build, _run_lecturer_build
    msg = await update.message.reply_text("⏳ Kurs-Index & Dozenten-Index werden neu aufgebaut...")
    try:
        # Wir führen die Builds hier asynchron aus
        count = await raumzeit.build_course_index()
        await msg.edit_text(f"✅ Kurs-Index: {count} Einträge\n⏳ Baue Dozenten-Index...")
        lecturer_count = await raumzeit.build_lecturer_index()
        await msg.edit_text(
            f"✅ Kurs-Index: {count} Einträge\n"
            f"✅ Dozenten-Index: {lecturer_count} gematcht"
        )
    except Exception as exc:
        log.exception("Index-Aufbau fehlgeschlagen")
        await msg.edit_text(f"⚠️ Fehler beim Index-Aufbau: {exc}")
