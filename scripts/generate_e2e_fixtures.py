import json
import asyncio
import os
import sys
from pathlib import Path

# Path setup to import src
sys.path.append(str(Path(__file__).parent.parent))

from src import tools, db

async def generate():
    print("🚀 Generiere dynamische E2E-Fixtures basierend auf Realdaten...")
    await db.init()
    
    # 1. Aktuelles Menü holen
    menu = await tools.get_mensa_menu()
    if menu.get("closed") or not menu.get("meals"):
        print("⚠️ Mensa heute geschlossen oder keine Daten. Nutze statische Fallbacks.")
        return

    # 2. Statische Cases laden
    static_path = Path("tests/fixtures/e2e_cases.json")
    with open(static_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # 3. Dynamische Anpassung
    meals = menu["meals"]
    
    # Finde ein Fleischgericht und ein vegetarisches/veganes Gericht für präzise Tests
    meat_meal = next((m for m in meals if not m.get("isVegetarian")), None)
    veg_meal = next((m for m in meals if m.get("isVegetarian")), None)
    
    for case in cases:
        if case["name"] == "Allergene Seelachs (Namens-Lookup)":
            if meat_meal:
                case["input"] = f"Welche Allergene hat {meat_meal['name']}?"
                case["expected_keywords"] = ["Allergene", meat_meal['name'][:15]]
                case["name"] = f"Allergene {meat_meal['name'][:20]} (Dynamisch)"
        
        if case["name"] == "Allergene Wahlessen 1 (Kein Trenner - Robustheitstext)":
            # Wir behalten diesen Test bei, aber stellen sicher, dass Wahlessen 1 existiert
            line_1_exists = any(m.get("line", {}).get("name") == "Wahlessen 1" for m in meals)
            if not line_1_exists:
                # Falls Wahlessen 1 heute nicht da ist, nimm die erste verfügbare Linie
                first_line = meals[0].get("line", {}).get("name", "Aktionstheke")
                case["input"] = f"Details zu {first_line.lower().replace(' ', '')}1"
                case["expected_keywords"] = ["Allergene", first_line]

    # 4. Speichern
    dynamic_path = Path("tests/fixtures/dynamic_e2e_cases.json")
    with open(dynamic_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Dynamische Fixtures gespeichert in {dynamic_path}")

if __name__ == "__main__":
    asyncio.run(generate())
