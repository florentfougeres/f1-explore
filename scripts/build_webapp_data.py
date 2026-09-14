#!/usr/bin/env python3
"""
Fusionne data/f1_calendars.csv et data/circuits.csv pour produire le JSON
consommé par la web app MapLibre (webapp/public/data/seasons.json), et
regroupe data/tracks/*.geojson en un seul webapp/public/data/tracks.geojson.

Usage :
    python build_webapp_data.py
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CALENDARS_CSV = DATA_DIR / "f1_calendars.csv"
CIRCUITS_CSV = DATA_DIR / "circuits.csv"
TRACKS_DIR = DATA_DIR / "tracks"
PUBLIC_DATA_DIR = Path(__file__).resolve().parent.parent / "webapp" / "public" / "data"
OUTPUT_JSON = PUBLIC_DATA_DIR / "seasons.json"
OUTPUT_TRACKS_JSON = PUBLIC_DATA_DIR / "tracks.geojson"


def load_circuits() -> dict[str, dict]:
    """Retourne un dict alias brut ("Nom , Lieu") -> infos géo du circuit
    (circuit_id/pays/coordonnées, communs à toutes les variantes de nom)."""
    alias_to_circuit = {}
    with open(CIRCUITS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            info = {
                "circuit_id": row["circuit_id"],
                "country": row["country"],
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
            }
            for alias in row["aliases"].split(";"):
                alias_to_circuit[alias] = info
    return alias_to_circuit


def split_raw_circuit(raw: str) -> tuple[str, str]:
    """Sépare le libellé brut "Nom , Lieu" en (nom, lieu) tel qu'affiché sur
    Wikipedia pour cette course précise (nom d'époque, ex: "A1-Ring" en 2000
    plutôt que le nom actuel "Red Bull Ring")."""
    name, _, location = raw.partition(" , ")
    return name, location


def build_tracks() -> set[str]:
    """Fusionne data/tracks/*.geojson en un seul FeatureCollection et
    retourne l'ensemble des circuit_id qui ont un tracé."""
    features = []
    circuit_ids_with_track = set()
    for path in sorted(TRACKS_DIR.glob("*.geojson")):
        fc = json.loads(path.read_text(encoding="utf-8"))
        for feature in fc["features"]:
            features.append(feature)
            circuit_ids_with_track.add(feature["properties"]["circuit_id"])

    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_TRACKS_JSON, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

    print(f"OK — {len(features)} tracés écrits dans {OUTPUT_TRACKS_JSON}")
    return circuit_ids_with_track


def main() -> None:
    circuits_by_alias = load_circuits()
    circuit_ids_with_track = build_tracks()

    seasons: dict[str, list[dict]] = {}
    with open(CALENDARS_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["Round"].strip().startswith("Source"):
                continue
            geo = circuits_by_alias.get(row["Circuit"])
            if geo is None:
                raise SystemExit(f"Circuit non reconnu : {row['Circuit']!r}")

            name, location = split_raw_circuit(row["Circuit"])
            year = row["Year"]
            seasons.setdefault(year, []).append({
                "round": int(row["Round"]),
                "grand_prix": row["Grand Prix"],
                "date": row["Date"],
                "name": name,
                "location": location,
                "has_track": geo["circuit_id"] in circuit_ids_with_track,
                **geo,
            })

    for races in seasons.values():
        races.sort(key=lambda r: r["round"])

    ordered = {year: seasons[year] for year in sorted(seasons, key=int)}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)

    total_races = sum(len(v) for v in ordered.values())
    print(f"OK — {len(ordered)} saisons, {total_races} courses écrites dans {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
