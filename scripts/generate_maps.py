import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import os
from pathlib import Path

# Pfade
PDF_PATH = "HKA_Lageplan_A4.pdf"
OUTPUT_DIR = Path("data/maps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Diese Koordinaten wurden manuell via scripts/calibrate_map.py verifiziert
# Die Nummern beziehen sich auf die vom Nutzer gewählten Kreise.
BUILDING_COORDS = {
    'A':  (385.0, 406.0),
    'B':  (282.5, 215.6),
    'HB': (276.1, 197.2),
    'LB': (321.2, 220.5),
    'C':  (340.0, 219.2),
    'E':  (227.5, 325.7),
    'HE': (198.3, 332.7),
    'F':  (229.8, 290.8),
    'K':  (308.8, 438.2),
    'LI': (200.7, 288.8),
    'M':  (231.8, 256.0)
}

def generate_maps():
    if not os.path.exists(PDF_PATH):
        print(f"Fehler: {PDF_PATH} nicht gefunden.")
        return

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    
    # Hochauflösendes Bild rendern
    zoom = 4 
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    print("Generiere final kalibrierte Lagepläne...")
    
    for b_code, (pdf_x, pdf_y) in BUILDING_COORDS.items():
        x = pdf_x * zoom
        y = pdf_y * zoom

        draw_img = img.copy()
        draw = ImageDraw.Draw(draw_img)
        
        # Stabiler roter Kreis um den Fundpunkt
        r = 80 
        draw.ellipse([x-r, y-r, x+r, y+r], outline="red", width=20)
        
        out_path = OUTPUT_DIR / f"map_{b_code}.png"
        draw_img.save(out_path)
        print(f"  -> {out_path} (Position: {pdf_x}/{pdf_y})")

    doc.close()
    print("\nFertig! Alle Karten sind jetzt perfekt kalibriert.")

if __name__ == "__main__":
    generate_maps()
