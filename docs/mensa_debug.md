# Mensa Debug Checklist

This document helps in diagnosing issues with the Mensa integration.

## 1. Common Query Examples
- **General Menu**: "Was gibt es heute in der Mensa?", "/mensa", "Speiseplan Moltke morgen"
- **Details**: "Welche Allergene hat das Seelachsfilet?", "Zusatzstoffe in der Currywurst"
- **Dietary**: "Gibt es heute was Veganes?", "Welche Gerichte sind vegetarisch?"

## 2. Expected Log Output
Check `logs/bot.txt` for the following patterns:

- `INFO src.tools: Mensa-API: Rufe Speiseplan ab (canteen=..., date=...)`
- `INFO src.tools: Mensa-API: Speiseplan erhalten in 1.2s (25 Gerichte)`
- `ERROR src.tools: Mensa-API Fehler: 500 Internal Server Error`

## 3. Data Integrity
- Check if `data/cache.db` contains data:
  ```bash
  sqlite3 data/cache.db "SELECT COUNT(*) FROM mensa_meals;"
  ```
- If the count is 0, run `/mensa` in Telegram to trigger a sync.

## 4. Known Edge Cases
- **Mensa Closed**: On weekends or holidays, the API returns an empty list or `getCanteen=null`. The bot should show a "Geschlossen" message.
- **ID Hallucination**: If the LLM tries to query `gut_guenstig_1`, the bot uses fuzzy matching to find the real UUID in the DB.
- **API Limits**: The Mensa-KA API is generally robust but might fail under heavy load.
