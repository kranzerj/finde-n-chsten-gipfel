#!/usr/bin/env python3
"""
find_elevation_points.py

Dieses Skript liest OpenStreetMap-Daten im PBF-Format einmalig ein, sammelt alle Gipfel (natural=peak)
und ermöglicht mehrfaches Abfragen mit geänderten Parametern (Mindesthöhe, Kreuzfilter, Dominanz).
Zweite und weitere Durchläufe sind deutlich schneller, da die Daten bereits im Speicher vorliegen.

Dominanz wird definiert als Luftlinienentfernung vom Gipfel bis zum nächstgelegenen höheren Punkt (in km).

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
    Speichert lat, lon, ele, name, summit_cross und prominence.
    """
    def __init__(self):
        super().__init__()
        self.peaks = []  # Liste von Dicts: lat, lon, ele, name, summit_cross, prominence

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
        prom_tag = n.tags.get('prominence')
        try:
            prominence = float(prom_tag) if prom_tag is not None else None
        except (ValueError, TypeError):
            prominence = None
        self.peaks.append({
            'lat': n.location.lat,
            'lon': n.location.lon,
            'ele': ele,
            'name': name,
            'summit_cross': summit_cross,
            'prominence': prominence
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


def compute_dominance(peak, all_peaks):
    """
    Berechnet die Dominanz eines Peaks als Entfernung zum nächstgelegenen höheren Peak.
    Gibt Dominanz in km zurück, oder float('inf') wenn kein höherer Peak existiert.
    """
    higher = [q for q in all_peaks if q['ele'] > peak['ele']]
    if not higher:
        return float('inf')
    # Minimum-Distanz zu einem höheren Gipfel
    distances = [geodesic((peak['lat'], peak['lon']), (q['lat'], q['lon'])).kilometers for q in higher]
    return min(distances)


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
    consider_dominance = prompt("Soll auch die Dominanz berücksichtigt werden? (y/n): ").strip().lower().startswith('y')

    # PLZ geokodieren
    print(f"Geokodiere PLZ {postal_code} in {country}...")
    nomi = pgeocode.Nominatim(country)
    res = nomi.query_postal_code(postal_code)
    if res is None or res.latitude is None or res.longitude is None:
        print(f"Fehler: PLZ {postal_code} in {country} nicht gefunden.")
        return
    start = (res.latitude, res.longitude)

    # Filtern nach Höhe und Kreuz
    filtered = [p for p in peaks if p['ele'] >= min_ele and (not summit_cross_only or p['summit_cross'])]
    if not filtered:
        print("Keine passenden Peaks gefunden.")
        return

    # Distanz zur Startposition berechnen
    dist_list = [(geodesic(start, (p['lat'], p['lon'])).kilometers, p) for p in filtered]
    # Sortiert nach Distanz
    dist_list.sort(key=lambda x: x[0])

    if consider_dominance:
        # Die 20 nächsten Peaks auswählen
        nearest20 = dist_list[:20]
        # Dominanz berechnen
        dom_list = []  # Liste von (dominance_km, dist_km, peak)
        for dist, p in nearest20:
            dom = compute_dominance(p, peaks)
            dom_list.append((dom, dist, p))
        # Sortieren nach Dominanz (absteigend, inf ganz oben)
        dom_list.sort(key=lambda x: x[0], reverse=True)
        print("\nDie 20 nächstgelegenen Peaks, sortiert nach Dominanz (in km):")
        for idx, (dom, dist, p) in enumerate(dom_list, start=1):
            dom_str = f"{dom:.2f}" if dom != float('inf') else "∞"
            prom = p['prominence'] or 0.0
            print(f"{idx}. {p['name']}: Höhe: {p['ele']:.1f} m, Prominenz: {prom:.1f} m, Dominanz: {dom_str} km, Distanz: {dist:.2f} km")
    else:
        # Standard: die 10 nächsten Peaks
        nearest10 = dist_list[:10]
        print("\nDie zehn nächstgelegenen Peaks:")
        for idx, (dist, p) in enumerate(nearest10, start=1):
            prom = p['prominence'] or 0.0
            print(f"{idx}. {p['name']}: Höhe: {p['ele']:.1f} m, Prominenz: {prom:.1f} m, Distanz: {dist:.2f} km")


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
