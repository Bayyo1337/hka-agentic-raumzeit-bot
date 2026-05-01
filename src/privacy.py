"""
GDPR/DSGVO Compliance Module für den Telegram Bot.
Implementiert Nutzer-Steuerung über Datenexport, Löschung und Privacy-Einstellungen.
"""

import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from src import db

log = logging.getLogger(__name__)

# --- Texte (UX) ---

PRIVACY_INFO = """
<b>🌌 Datenschutz & Privatsphäre</b>

Deine Daten gehören dir. Hier ist eine Übersicht, was dieser Bot speichert und warum:

<b>1. Welche Daten werden gespeichert?</b>
• <b>Profil:</b> Telegram ID, Vorname, Nutzername und deine gewählten Kurse (für Personalisierung).
• <b>Verlauf:</b> Die letzten Chat-Nachrichten (für Kontext-Verständnis der KI).
• <b>Nutzung:</b> Zeitpunkte deiner Anfragen (für Rate-Limiting).
• <b>Tokens:</b> Zähler der verbrauchten KI-Einheiten.

<b>2. Wo liegen die Daten?</b>
• Alle Daten liegen in verschlüsselten SQLite-Datenbanken auf einem privaten Server in Deutschland.
• Es findet <u>kein</u> Tracking durch Drittanbieter statt (außer Telegram selbst).

<b>3. Drittanbieter</b>
• <b>Telegram:</b> Empfängt deine Nachrichten technisch bedingt.
• <b>KI-Provider (Mistral/OpenAI):</b> Empfängt anonymisierte Anfragen zur Verarbeitung.

<b>4. Deine Rechte</b>
Nutze /data für eine Übersicht, /export für deine Daten oder /delete zum Löschen.
Details findest du unter: <a href="https://github.com/Bayyo1337/hka-agentic-raumzeit-bot/blob/gemini/docs/DSGVO.md">Vollständige Datenschutzerklärung</a>
"""

async def cmd_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Datenschutz-Informationen an."""
    await update.message.reply_html(PRIVACY_INFO, disable_web_page_preview=True)


async def cmd_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt eine Übersicht der gespeicherten Daten des Nutzers."""
    user_id = update.effective_user.id
    profile = await db.get_user(user_id)
    history = await db.load_history(user_id)
    tokens = await db.get_tokens(user_id)
    settings = await db.get_privacy_settings(user_id)
    
    # Kurse zählen
    course_config = await db.get_user_course_config(user_id)
    course_list = ", ".join([c["key"] for c in course_config]) or "Keine"

    text = f"""
<b>📊 Deine gespeicherten Daten</b>

• <b>ID:</b> <code>{user_id}</code>
• <b>Name:</b> {profile.get('first_name', 'N/A')} (@{profile.get('username', 'N/A')})
• <b>Gespeicherte Kurse:</b> {course_list}
• <b>Chat-Verlauf:</b> {len(history)} Nachrichten gespeichert.
• <b>Token-Verbrauch:</b> {tokens[0] + tokens[1]} (In: {tokens[0]}, Out: {tokens[1]})
• <b>Status:</b> {"Aktiv" if not profile.get('banned') else "Gesperrt"}

<b>⚙️ Deine Einstellungen:</b>
• Profil-Speicherung: {"✅ An" if settings['allow_profile'] else "❌ Aus"}
• Verlauf-Speicherung: {"✅ An" if settings['allow_history'] else "❌ Aus"}
• KI-Verarbeitung: {"✅ An" if settings['allow_llm'] else "❌ Aus"}
• Telemetrie: {"✅ An" if settings['allow_telemetry'] else "❌ Aus"}

<b>🕒 Aufbewahrung (TTL):</b>
• Verlauf: {settings['history_ttl_hours']}h
• Telemetrie: {settings['telemetry_ttl_hours']}h

Nutze /consent zum Ändern oder /export für das JSON-Format.
"""
    await update.message.reply_html(text)


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exportiert alle Nutzerdaten als JSON-Datei."""
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Bereite Daten-Export vor...")
    
    data = await db.export_user_data(user_id)
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    from io import BytesIO
    bio = BytesIO(json_str.encode("utf-8"))
    bio.name = f"raumzeit_data_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
    
    await update.message.reply_document(
        document=bio,
        caption="📦 Dein vollständiger Datensatz gemäß DSGVO Art. 20 (Datenübertragbarkeit).",
        filename=bio.name
    )


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiiert den Löschvorgang."""
    keyboard = [
        [
            InlineKeyboardButton("🔥 Ja, alles löschen", callback_query_handler_data="privacy_delete_confirm"),
            InlineKeyboardButton("❌ Abbrechen", callback_query_handler_data="privacy_delete_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ <b>ACHTUNG:</b> Möchtest du wirklich alle deine Daten unwiderruflich löschen?\n\n"
        "Dies umfasst:\n"
        "• Dein Profil & gespeicherte Kurse\n"
        "• Deinen gesamten Chat-Verlauf\n"
        "• Alle Token-Statistiken\n"
        "• Deine Einstellungen\n\n"
        "Dein Bot-Zugang wird damit effektiv zurückgesetzt.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def handle_privacy_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Bestätigungen für Löschung und Consent-Änderungen."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "privacy_delete_confirm":
        await db.delete_user_data(user_id)
        await query.edit_message_text("🗑 <b>Erfolgreich gelöscht.</b> Alle deine Daten wurden aus dem System entfernt.", parse_mode="HTML")
        log.info("User %d deleted their data via /delete", user_id)
        return

    if data == "privacy_delete_cancel":
        await query.edit_message_text("✅ Löschvorgang abgebrochen.")
        return

    if data.startswith("privacy_toggle_"):
        field = data.replace("privacy_toggle_", "")
        settings = await db.get_privacy_settings(user_id)
        if field in settings:
            settings[field] = not settings[field]
            await db.set_privacy_settings(user_id, settings)
            await query.answer(f"{field} geändert!")
            # Menü neu zeichnen
            await show_consent_menu(query, user_id)


async def cmd_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt das Consent-Einstellungsmenü."""
    user_id = update.effective_user.id
    await show_consent_menu(update.message, user_id, is_new=True)

async def show_consent_menu(target, user_id, is_new=False):
    settings = await db.get_privacy_settings(user_id)
    
    keyboard = [
        [InlineKeyboardButton(f"Profil speichern: {'✅' if settings['allow_profile'] else '❌'}", callback_data="privacy_toggle_allow_profile")],
        [InlineKeyboardButton(f"Verlauf speichern: {'✅' if settings['allow_history'] else '❌'}", callback_data="privacy_toggle_allow_history")],
        [InlineKeyboardButton(f"KI-Verarbeitung: {'✅' if settings['allow_llm'] else '❌'}", callback_data="privacy_toggle_allow_llm")],
        [InlineKeyboardButton(f"Telemetrie: {'✅' if settings['allow_telemetry'] else '❌'}", callback_data="privacy_toggle_allow_telemetry")],
        [InlineKeyboardButton("Fertig", callback_data="privacy_delete_cancel")] # Reuse cancel to just close/done
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "<b>⚙️ Privacy-Einstellungen</b>\n\nWähle aus, welche Daten der Bot verarbeiten darf:"
    
    if is_new:
        await target.reply_html(text, reply_markup=reply_markup)
    else:
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def cmd_retention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Erlaubt das Einstellen der Aufbewahrungsfristen."""
    # Vereinfacht: Zeige aktuelle Fristen und biete Buttons für Presets
    user_id = update.effective_user.id
    settings = await db.get_privacy_settings(user_id)
    
    text = f"""
<b>🕒 Aufbewahrungsfristen (Retention)</b>

Hier kannst du festlegen, wie lange deine Daten gespeichert bleiben:

• <b>Chat-Verlauf:</b> {settings['history_ttl_hours']}h
• <b>Telemetrie-Logs:</b> {settings['telemetry_ttl_hours']}h
• <b>Plan-Cache:</b> {settings['plan_cache_ttl_hours']}h
• <b>Feedback:</b> {settings['feedback_ttl_days']} Tage

<i>Kürzere Fristen erhöhen den Datenschutz, längere Fristen verbessern die KI-Konstanz und Performance.</i>
"""
    keyboard = [
        [InlineKeyboardButton("Minimal (24h History)", callback_data="privacy_preset_min")],
        [InlineKeyboardButton("Standard (1 Woche History)", callback_data="privacy_preset_std")],
        [InlineKeyboardButton("Maximal (1 Monat History)", callback_data="privacy_preset_max")],
    ]
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_retention_presets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    settings = await db.get_privacy_settings(user_id)
    if data == "privacy_preset_min":
        settings.update({"history_ttl_hours": 24, "telemetry_ttl_hours": 2, "feedback_ttl_days": 7})
    elif data == "privacy_preset_std":
        settings.update({"history_ttl_hours": 168, "telemetry_ttl_hours": 24, "feedback_ttl_days": 30})
    elif data == "privacy_preset_max":
        settings.update({"history_ttl_hours": 720, "telemetry_ttl_hours": 168, "feedback_ttl_days": 90})
        
    await db.set_privacy_settings(user_id, settings)
    await query.answer("Preset angewendet!")
    await query.edit_message_text(f"✅ Aufbewahrungsfristen wurden auf <b>{data.split('_')[-1]}</b> gesetzt.", parse_mode="HTML")


def register_handlers(app):
    """Registriert alle Privacy-Handler in der Application."""
    app.add_handler(CommandHandler(["privacy", "datenschutz"], cmd_privacy))
    app.add_handler(CommandHandler(["data", "me"], cmd_data))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("consent", cmd_consent))
    app.add_handler(CommandHandler("retention", cmd_retention))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_privacy_callbacks, pattern="^privacy_(delete|toggle)_"))
    app.add_handler(CallbackQueryHandler(handle_retention_presets, pattern="^privacy_preset_"))
