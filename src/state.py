"""
Globaler Status für den Raumzeit-Bot.
"""
from datetime import datetime

_BOT_START = datetime.now()

# Wartungsmodus: (aktiv, Nachricht)
_maintenance: list = [False, "🔧 Der Bot wird gerade gewartet. Bitte versuche es später."]
