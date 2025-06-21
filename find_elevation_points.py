#!/usr/bin/env python3
"""
find_elevation_points.py

Dieses Skript liest OpenStreetMap-Daten im PBF-Format ein, sammelt alle Gipfel (natural=peak)
und ermöglicht mehrfaches Abfragen mit geänderten Parametern
(Mindesthöhe, Kreuzfilter, Dominanz und Erreichbarkeit per Klettersteig).

Dominanz: Luftlinienentfernung zum nächsthöheren Peak (in km).
Klettersteig-Erreichbarkeit: Ein via_ferrata-Segment innerhalb von THRESHOLD_DISTANCE Metern Luftlinie
vom Gipfel zählt als erreichbar.

Abhängigkeiten:
    pip install osmium pgeocode geopy
"""
import osmium
import pgeocode
from geopy.distance import geodesic
import sys

# Globale Variable für Klettersteig-Umkreis
#THRESHOLD_DISTANCE = 666  # Standard (Meter)


def prompt(msg):
    try:
        return input(msg)
    except EOFError:
        print("Eingabe fehlgeschlagen. Bitte erneut starten.")
        sys.exit(1)

class PeakLoader(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.peaks = []
    def node(self, n):
        if n.tags.get('natural') != 'peak': return
        ele_tag = n.tags.get('ele')
        if ele_tag is None: return
        try:
            ele = float(ele_tag)
        except (ValueError, TypeError): return
        if not n.location.valid(): return
        self.peaks.append({
            'lat': n.location.lat,
            'lon': n.location.lon,
            'ele': ele,
            'name': n.tags.get('name', '<kein Name>'),
            'summit_cross': n.tags.get('summit:cross', '').lower() == 'yes'
        })

class ViaFerrataLoader(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.segments = []
    def way(self, w):
        if w.tags.get('highway') != 'via_ferrata': return
        try:
            scale = int(w.tags.get('via_ferrata_scale', ''))
        except (ValueError, TypeError):
            scale = None
        coords = [(n.location.lat, n.location.lon) for n in w.nodes if n.location.valid()]
        if coords:
            self.segments.append({'coords': coords, 'scale': scale})


def load_peaks(map_file):
    print(f"Lade OSM-Datei '{map_file}' und sammle alle Peaks...")
    loader = PeakLoader()
    loader.apply_file(map_file, locations=True)
    print(f"Insgesamt {len(loader.peaks)} Peaks geladen.")
    return loader.peaks


def load_via_ferrata(map_file):
    print(f"Lade via_ferrata-Segmente aus '{map_file}'...")
    loader = ViaFerrataLoader()
    loader.apply_file(map_file, locations=True)
    print(f"Insgesamt {len(loader.segments)} via_ferrata-Segmente geladen.")
    return loader.segments


def compute_dominance(peaks, peak):
    higher = [p for p in peaks if p['ele'] > peak['ele']]
    if not higher:
        return float('inf')
    return min(
        geodesic((peak['lat'], peak['lon']), (p['lat'], p['lon'])).kilometers
        for p in higher
    )


def is_reachable_via(peak, vf_segments, max_scale):
    for seg in vf_segments:
        if seg['scale'] is None or seg['scale'] <= max_scale:
            for lat, lon in seg['coords']:
                if geodesic((peak['lat'], peak['lon']), (lat, lon)).meters <= THRESHOLD_DISTANCE:
                    return True
    return False


def run_query(peaks, vf_segments):
    country = prompt("Startland (z.B.: AT): ").strip().upper()
    postal_code = prompt("Start PLZ (z.B.: 4363): ").strip()
    try:
        min_ele = float(prompt("Höhenmeter Gipfel (z.B.: 1300): ").strip())
    except ValueError:
        print("Ungültige Höhe. Bitte eine Zahl eingeben.")
        return vf_segments
    cross_only = prompt("Nur Gipfel mit Kreuz? (y/n): ").strip().lower().startswith('y')
    dominance = prompt("Dominanz berücksichtigen? (y/n): ").strip().lower().startswith('y')
    via_only = prompt("Nur via_ferrata erreichbar? (y/n): ").strip().lower().startswith('y')
    max_scale = None
    if via_only and not vf_segments:
        vf_segments = load_via_ferrata(map_file)
    if via_only:
        try:
            max_scale = int(prompt("Maximale Schwierigkeit (0–6): ").strip())
        except ValueError:
            print("Ungültige Skala. Ignoriere via_ferrata-Filter.")
            via_only = False
    print(f"Geokodiere PLZ {postal_code} in {country}...")
    nomi = pgeocode.Nominatim(country)
    res = nomi.query_postal_code(postal_code)
    if res is None or res.latitude is None or res.longitude is None:
        print(f"Fehler: PLZ {postal_code} in {country} nicht gefunden.")
        return vf_segments
    start = (res.latitude, res.longitude)
    print(f"Startkoordinaten: {start[0]:.5f}, {start[1]:.5f}")
    candidates = [p for p in peaks if p['ele'] >= min_ele and (not cross_only or p['summit_cross'])]
    print(f"Kandidaten nach Höhe und Kreuz: {len(candidates)}")
    if via_only:
        before = len(candidates)
        candidates = [p for p in candidates if is_reachable_via(p, vf_segments, max_scale)]
        print(f"Kandidaten nach via_ferrata-Filter: {len(candidates)} (vorher {before})")
    if not candidates:
        print("Keine passenden Peaks gefunden.")
        return vf_segments
    dist_list = [(geodesic(start, (p['lat'], p['lon'])).kilometers, p) for p in candidates]
    dist_list.sort(key=lambda x: x[0])
    if dominance:
        nearest20 = dist_list[:20]
        dom_list = [(compute_dominance(peaks, p), dist, p) for dist, p in nearest20]
        dom_list.sort(key=lambda x: x[0], reverse=True)
        print("\n20 nächstgelegene Peaks, sortiert nach Dominanz (km):")
        for idx, (dom, dist, p) in enumerate(dom_list, start=1):
            dom_str = f"{dom:.2f}" if dom != float('inf') else '∞'
            print(f"{idx}. {p['name']}: Höhe {p['ele']:.1f} m, Dominanz {dom_str} km, Distanz {dist:.2f} km")
    else:
        nearest10 = dist_list[:10]
        print("\nDie zehn nächstgelegenen Peaks:")
        for idx, (dist, p) in enumerate(nearest10, start=1):
            print(f"{idx}. {p['name']}: Höhe {p['ele']:.1f} m, Distanz {dist:.2f} km")
    return vf_segments


def main():
    global map_file, THRESHOLD_DISTANCE
    # Kartendatei abfragen, Beispiel: max.pbf
    map_file = prompt("Kartendatei (z.B.: max.pbf): ").strip()
    use_via = prompt("Klettersteige initial laden? (y/n): ").strip().lower().startswith('y')
    # Threshold nur abfragen, wenn via_ferrata-Filter genutzt werden soll
    if use_via:
        try:
            THRESHOLD_DISTANCE = float(prompt("Maximale Entfernung zum Klettersteig in Metern (z.B. 333): ").strip())
        except ValueError:
            print(f"Ungültige Zahl, verwende Standard {THRESHOLD_DISTANCE} m.")
    peaks = load_peaks(map_file)
    vf_segments = []
    if use_via:
        vf_segments = load_via_ferrata(map_file)
    while True:
        vf_segments = run_query(peaks, vf_segments)
        if not prompt("Möchtest du eine weitere Abfrage durchführen? (y/n): ").strip().lower().startswith('y'):
            print("Programm beendet.")
            break

if __name__ == "__main__":
    main()
