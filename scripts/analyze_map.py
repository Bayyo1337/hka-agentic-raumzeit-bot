import fitz  # PyMuPDF

def analyze_red_buildings():
    doc = fitz.open("HKA_Lageplan_A4.pdf")
    page = doc[0]
    
    # Wir suchen nach Pfaden (Vektorgrafiken)
    paths = page.get_drawings()
    print(f"Gefundene Grafik-Pfade: {len(paths)}")
    
    # HKA-Rot ist ca. (0.76, 0.11, 0.18) in RGB
    # Wir suchen Objekte, die gefüllt sind und eine rötliche Farbe haben
    red_objects = []
    for i, path in enumerate(paths):
        fill_color = path.get("fill")
        if fill_color:
            r, g, b = fill_color
            # Grober Check auf Rot-Dominanz
            if r > 0.6 and g < 0.3 and b < 0.3:
                rect = path["rect"]
                center_x = (rect.x0 + rect.x1) / 2
                center_y = (rect.y0 + rect.y1) / 2
                red_objects.append((center_x, center_y))
                print(f"Rotes Objekt gefunden bei: x={center_x:.1f}, y={center_y:.1f}")

    # Jetzt suchen wir die Buchstaben in der Nähe dieser Punkte
    buildings = ["A", "B", "C", "D", "E", "F", "K", "M", "LI", "HO", "P"]
    final_coords = {}

    for b_code in buildings:
        text_instances = page.search_for(b_code)
        # Finde die Text-Instanz, die am nächsten an einem roten Objekt liegt
        best_dist = 9999
        best_coord = None
        
        for inst in text_instances:
            tx = (inst.x0 + inst.x1) / 2
            ty = (inst.y0 + inst.y1) / 2
            
            for rx, ry in red_objects:
                dist = ((tx - rx)**2 + (ty - ry)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best_coord = (rx, ry)
        
        if best_coord and best_dist < 50: # Nur wenn ein rotes Objekt nah genug ist
            final_coords[b_code] = best_coord
            print(f"✅ Gebäude {b_code} erfolgreich gemappt: {best_coord}")

    print("\n--- Kopiere dies in scripts/generate_maps.py ---")
    print(final_coords)

if __name__ == "__main__":
    analyze_red_buildings()
