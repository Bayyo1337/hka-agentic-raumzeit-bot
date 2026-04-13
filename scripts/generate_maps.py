import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import os
from pathlib import Path

# Pfade
PDF_PATH = "HKA_Lageplan_A4.pdf"
OUTPUT_DIR = Path("data/maps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_maps():
    if not os.path.exists(PDF_PATH):
        print(f"Fehler: {PDF_PATH} nicht gefunden.")
        return

    # PDF öffnen
    doc = fitz.open(PDF_PATH)
    page = doc[0]
    
    # Hochauflösendes Bild rendern (300 DPI)
    zoom = 4 # 72 * 4 = 288 DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Wichtige Gebäude und deren (geschätzte) Suchbegriffe/Positionen
    # Wir versuchen zuerst, den Text im PDF zu finden, um exakte Koordinaten zu erhalten.
    buildings = ["A", "B", "C", "D", "E", "F", "K", "M", "LI", "HO", "P"]
    
    print("Generiere Lagepläne...")
    
    for b_code in buildings:
        # Suche Text im PDF (originale Koordinaten)
        text_instances = page.search_for(b_code)
        
        # Falls Text gefunden wurde, nutzen wir die Koordinaten
        if text_instances:
            # Wir nehmen die erste Fundstelle
            inst = text_instances[0]
            # Umrechnen auf Zoom-Pixel
            x = (inst.x0 + inst.x1) / 2 * zoom
            y = (inst.y0 + inst.y1) / 2 * zoom
        else:
            # Fallback: Falls Text nicht im PDF suchbar ist, nutzen wir manuelle Offsets 
            # (Diese müssten normalerweise verifiziert werden, hier als Platzhalter)
            continue

        # Kopie des Originalbilds erstellen
        draw_img = img.copy()
        draw = ImageDraw.Draw(draw_img)
        
        # Roten Kreis zeichnen
        r = 60 # Radius des Kreises
        draw.ellipse([x-r, y-r, x+r, y+r], outline="red", width=15)
        
        # Speichern
        out_path = OUTPUT_DIR / f"map_{b_code}.png"
        draw_img.save(out_path)
        print(f"  -> {out_path} erstellt.")

    doc.close()
    print("\nFertig! Alle Karten wurden in data/maps/ gespeichert.")

if __name__ == "__main__":
    generate_maps()
