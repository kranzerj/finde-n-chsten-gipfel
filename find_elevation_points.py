#!/usr/bin/env python3
"""
find_elevation_points.py

Dieses Skript liest OpenStreetMap-Daten im PBF-Format ein, sammelt alle Gipfel (natural=peak) über einer angegebenen Höhenmeter-Grenze
und liefert die zehn nächstgelegenen Punkte relativ zur Start-PLZ aus.
Optional kann auf Gipfel mit Kreuz (Tag summit:cross=yes) gefiltert werden.

Ausgabe enthält jetzt auch den Namen des Gipfels (Tag 'name').

Abhängigkeiten:
    pip install osmium pgeocode geopy
"""
import osmium
import pgeocode
from geopy.distance import geodesic
import sys


def prompt(msg):
    try:
        return input(msg)
    except EOFError:
        print("Eingabe fehlgeschlagen. Bitte erneut starten.")
        sys.exit(1)

class PeakCollector(osmium.SimpleHandler):
    def __init__(self, min_ele, summit_cross_only):
        super().__init__()
        self.min_ele = min_ele
        self.summit_cross_only = summit_cross_only
        # Liste von (lat, lon, ele, name)
        self.points = []

    def node(self, n):
        # Nur Peaks (natural=peak)
        if n.tags.get('natural') != 'peak':
            return
        # Optional: nur mit Gipfelkreuz
        if self.summit_cross_only and n.tags.get('summit:cross', '').lower() != 'yes':
            return
        # Höhenangabe prüfen
        ele_tag = n.tags.get('ele')
        if ele_tag is None:
            return
        try:
            ele = float(ele_tag)
        except (ValueError, TypeError):
            return
        # Position prüfen
        if ele >= self.min_ele and n.location.valid():
            name = n.tags.get('name', '<kein Name>')
            self.points.append((n.location.lat, n.location.lon, ele, name))


def main():
    # Eingaben abfragen
    map_file = prompt("Kartendatei (z.B.: extract2.pbf): ").strip()
    country = prompt("Startland (z.B.: AT): ").strip().upper()
    postal_code = prompt("Start PLZ (z.B.: 4363): ").strip()
    try:
        min_ele = float(prompt("Höhenmeter Gipfel (z.B.: 1300): ").strip())
    except ValueError:
        print("Ungültige Höhe. Bitte eine Zahl eingeben.")
        sys.exit(1)
    # Filter für Gipfelkreuz
    summit_cross_only = prompt("Nur Gipfel mit Kreuz (summit:cross=yes) suchen? (y/n): ").strip().lower().startswith('y')

    # PLZ geokodieren
    print(f"Geokodiere PLZ {postal_code} in {country}...")
    nomi = pgeocode.Nominatim(country)
    res = nomi.query_postal_code(postal_code)
    if res is None or res.latitude is None or res.longitude is None:
        print(f"Fehler: PLZ {postal_code} in {country} nicht gefunden.")
        sys.exit(1)
    start = (res.latitude, res.longitude)
    print(f"Startkoordinaten: {start[0]:.5f}, {start[1]:.5f}")

    # OSM-Daten parsen
    print(f"Lade OSM-Datei '{map_file}' und suche Peaks ≥ {min_ele} m{' mit Kreuz' if summit_cross_only else ''}...")
    handler = PeakCollector(min_ele, summit_cross_only)
    try:
        handler.apply_file(map_file)
    except Exception as e:
        print(f"Fehler beim Lesen der Datei: {e}")
        sys.exit(1)

    total = len(handler.points)
    print(f"Gefundene Peaks ≥ {min_ele} m: {total}")
    if total == 0:
        print("Keine passenden Peaks gefunden. Ende.")
        sys.exit(0)

    # Distanzen berechnen und sortieren
    dists = []  # Liste von (dist_km, lat, lon, ele, name)
    for lat, lon, ele, name in handler.points:
        dist = geodesic(start, (lat, lon)).kilometers
        dists.append((dist, lat, lon, ele, name))
    dists.sort(key=lambda x: x[0])
    top10 = dists[:10]

    # Ausgabe
    print("\nDie zehn nächstgelegenen Peaks:")
    for idx, (dist, lat, lon, ele, name) in enumerate(top10, start=1):
        print(f"{idx}. {name}: Koordinaten: ({lat:.5f}, {lon:.5f}), Höhe: {ele:.1f} m, Distanz: {dist:.2f} km")

if __name__ == "__main__":
    main()
