#!/usr/bin/env python3
"""
find_elevation_points.py

Dieses Skript liest OpenStreetMap-Daten im PBF-Format einmalig ein, sammelt alle Gipfel (natural=peak)
und ermöglicht mehrfaches Abfragen mit geänderten Parametern (Mindesthöhe und Kreuzfilter).
Zweite und weitere Durchläufe sind deutlich schneller, da die Daten bereits im Speicher vorliegen.

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

class PeakLoader(osmium.SimpleHandler):
    """
    Lädt alle OSM-Nodes mit natural=peak und speichert sie.
    Zusätzlich wird gemerkt, ob es ein Gipfelkreuz-Tag summit:cross=yes gibt.
    """
    def __init__(self):
        super().__init__()
        # Liste von Dictionaries: lat, lon, ele, name, summit_cross
        self.peaks = []

    def node(self, n):
        if n.tags.get('natural') != 'peak':
            return
        ele_tag = n.tags.get('ele')
        if ele_tag is None:
            return
        try:
            ele = float(ele_tag)
        except (ValueError, TypeError):
            return
        if not n.location.valid():
            return
        name = n.tags.get('name', '<kein Name>')
        summit_cross = (n.tags.get('summit:cross', '').lower() == 'yes')
        self.peaks.append({
            'lat': n.location.lat,
            'lon': n.location.lon,
            'ele': ele,
            'name': name,
            'summit_cross': summit_cross
        })


def load_peaks(map_file):
    print(f"Lade OSM-Datei '{map_file}' und sammle alle Peaks...")
    loader = PeakLoader()
    try:
        loader.apply_file(map_file)
    except Exception as e:
        print(f"Fehler beim Lesen der Datei: {e}")
        sys.exit(1)
    count = len(loader.peaks)
    print(f"Insgesamt {count} Peaks geladen.")
    return loader.peaks


def run_query(peaks):
    # Eingaben für diesen Durchlauf
    country = prompt("Startland (z.B.: AT): ").strip().upper()
    postal_code = prompt("Start PLZ (z.B.: 4363): ").strip()
    try:
        min_ele = float(prompt("Höhenmeter Gipfel (z.B.: 1300): ").strip())
    except ValueError:
        print("Ungültige Höhe. Bitte eine Zahl eingeben.")
        return
    summit_cross_only = prompt("Nur Gipfel mit Kreuz (summit:cross=yes) suchen? (y/n): ").strip().lower().startswith('y')

    # PLZ geokodieren
    print(f"Geokodiere PLZ {postal_code} in {country}...")
    nomi = pgeocode.Nominatim(country)
    res = nomi.query_postal_code(postal_code)
    if res is None or res.latitude is None or res.longitude is None:
        print(f"Fehler: PLZ {postal_code} in {country} nicht gefunden.")
        return
    start = (res.latitude, res.longitude)

    # Filtern und Entfernungen berechnen
    filtered = [p for p in peaks if p['ele'] >= min_ele and (not summit_cross_only or p['summit_cross'])]
    if not filtered:
        print("Keine passenden Peaks gefunden.")
        return
    dists = []
    for p in filtered:
        dist = geodesic(start, (p['lat'], p['lon'])).kilometers
        dists.append((dist, p))
    dists.sort(key=lambda x: x[0])
    top10 = dists[:10]

    # Ausgabe
    print("\nDie zehn nächstgelegenen Peaks:")
    for idx, (dist, p) in enumerate(top10, start=1):
        name = p['name']
        print(f"{idx}. {name}: Koordinaten: ({p['lat']:.5f}, {p['lon']:.5f}), Höhe: {p['ele']:.1f} m, Distanz: {dist:.2f} km")


def main():
    map_file = prompt("Kartendatei (z.B.: extract2.pbf): ").strip()
    peaks = load_peaks(map_file)

    while True:
        run_query(peaks)
        again = prompt("Möchtest du eine weitere Abfrage durchführen? (y/n): ").strip().lower()
        if again != 'y':
            print("Programm beendet.")
            break

if __name__ == "__main__":
    main()
