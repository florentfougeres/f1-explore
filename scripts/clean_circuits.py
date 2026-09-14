#!/usr/bin/env python3
"""
Construit un référentiel "un circuit = une ligne = un point sur la carte" à
partir des valeurs brutes de la colonne "Circuit" de data/f1_calendars.csv.

Le scraping Wikipedia produit des variantes multiples pour un même circuit
physique (nom officiel qui change avec les sponsors/rebranding, ville vs
région, orthographe avec/sans accent...). Ce script regroupe ces variantes
sous un identifiant canonique unique, avec pays + coordonnées approximatives
(utiles pour une carte), et conserve la liste des libellés bruts d'origine
("aliases") pour pouvoir refaire la jointure avec f1_calendars.csv.

Usage :
    python clean_circuits.py
    -> écrit data/circuits.csv
"""

import csv
import sys
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CALENDARS_CSV = DATA_DIR / "f1_calendars.csv"
OUTPUT_CSV = DATA_DIR / "circuits.csv"

# Chaque entrée regroupe un ou plusieurs libellés bruts "Nom , Lieu" observés
# dans f1_calendars.csv sous un même circuit physique.
# Coordonnées approximatives (niveau piste), à vérifier avant tout usage
# nécessitant une précision cartographique fine.
CIRCUITS = [
    dict(name="Albert Park Circuit", location="Melbourne", country="Australia",
         lat=-37.8497, lon=144.9680,
         aliases=["Albert Park Circuit , Melbourne"]),
    dict(name="Autódromo José Carlos Pace", location="São Paulo", country="Brazil",
         lat=-23.7036, lon=-46.6997,
         aliases=["Autódromo José Carlos Pace , São Paulo",
                  "Interlagos Circuit , São Paulo"]),
    dict(name="Autodromo Enzo e Dino Ferrari", location="Imola", country="Italy",
         lat=44.3439, lon=11.7167,
         aliases=["Autodromo Enzo e Dino Ferrari , Imola",
                  "Autodromo Internazionale Enzo e Dino Ferrari , Imola",
                  "Imola Circuit , Imola"]),
    dict(name="Silverstone Circuit", location="Silverstone", country="United Kingdom",
         lat=52.0786, lon=-1.0169,
         aliases=["Silverstone Circuit , Silverstone"]),
    dict(name="Circuit de Barcelona-Catalunya", location="Montmeló", country="Spain",
         lat=41.5700, lon=2.2611,
         aliases=["Circuit de Catalunya , Montmeló",
                  "Circuit de Barcelona-Catalunya , Montmeló"]),
    dict(name="Nürburgring", location="Nürburg", country="Germany",
         lat=50.3356, lon=6.9475,
         aliases=["Nürburgring , Nürburg"]),
    dict(name="Circuit de Monaco", location="Monte Carlo", country="Monaco",
         lat=43.7347, lon=7.4206,
         aliases=["Circuit de Monaco , Monaco",
                  "Circuit de Monaco , Monte Carlo",
                  "Circuit de Monaco , Monte-Carlo"]),
    dict(name="Circuit Gilles Villeneuve", location="Montréal", country="Canada",
         lat=45.5000, lon=-73.5228,
         aliases=["Circuit Gilles Villeneuve , Montreal",
                  "Circuit Gilles Villeneuve , Montréal"]),
    dict(name="Circuit de Nevers Magny-Cours", location="Magny-Cours", country="France",
         lat=46.8642, lon=3.1633,
         aliases=["Circuit de Nevers Magny-Cours , Magny-Cours",
                  "Circuit de Nevers Magny-Cours , Magny Cours"]),
    dict(name="Red Bull Ring", location="Spielberg", country="Austria",
         lat=47.2197, lon=14.7647,
         aliases=["A1-Ring , Spielberg",
                  "Red Bull Ring , Spielberg"]),
    dict(name="Hockenheimring", location="Hockenheim", country="Germany",
         lat=49.3278, lon=8.5656,
         aliases=["Hockenheimring , Hockenheim"]),
    dict(name="Hungaroring", location="Mogyoród", country="Hungary",
         lat=47.5789, lon=19.2486,
         aliases=["Hungaroring , Mogyoród"]),
    dict(name="Circuit de Spa-Francorchamps", location="Stavelot", country="Belgium",
         lat=50.4372, lon=5.9714,
         aliases=["Circuit de Spa-Francorchamps , Stavelot"]),
    dict(name="Autodromo Nazionale di Monza", location="Monza", country="Italy",
         lat=45.6156, lon=9.2811,
         aliases=["Autodromo Nazionale di Monza , Monza",
                  "Autodromo Nazionale Monza , Monza",
                  "Monza Circuit , Monza"]),
    dict(name="Indianapolis Motor Speedway", location="Speedway", country="United States",
         lat=39.7950, lon=-86.2347,
         aliases=["Indianapolis Motor Speedway , Speedway"]),
    dict(name="Suzuka Circuit", location="Suzuka", country="Japan",
         lat=34.8431, lon=136.5410,
         aliases=["Suzuka Circuit , Suzuka",
                  "Suzuka International Racing Course , Suzuka"]),
    dict(name="Sepang International Circuit", location="Sepang", country="Malaysia",
         lat=2.7608, lon=101.7383,
         aliases=["Sepang International Circuit , Sepang",
                  "Sepang International Circuit , Kuala Lumpur",
                  "Sepang International Circuit , Selangor"]),
    dict(name="Bahrain International Circuit", location="Sakhir", country="Bahrain",
         lat=26.0325, lon=50.5106,
         aliases=["Bahrain International Circuit , Sakhir"]),
    dict(name="Shanghai International Circuit", location="Shanghai", country="China",
         lat=31.3389, lon=121.2200,
         aliases=["Shanghai International Circuit , Shanghai"]),
    dict(name="Istanbul Park", location="Istanbul", country="Turkey",
         lat=40.9517, lon=29.4050,
         aliases=["Istanbul Park , Istanbul",
                  "Istanbul Park , Tuzla"]),
    dict(name="Fuji Speedway", location="Oyama, Shizuoka", country="Japan",
         lat=35.3717, lon=138.9267,
         aliases=["Fuji Speedway , Oyama, Shizuoka"]),
    dict(name="Valencia Street Circuit", location="Valencia", country="Spain",
         lat=39.4589, lon=-0.3313,
         aliases=["Valencia Street Circuit , Valencia"]),
    dict(name="Marina Bay Street Circuit", location="Singapore", country="Singapore",
         lat=1.2914, lon=103.8640,
         aliases=["Marina Bay Street Circuit , Singapore"]),
    dict(name="Yas Marina Circuit", location="Abu Dhabi", country="United Arab Emirates",
         lat=24.4672, lon=54.6031,
         aliases=["Yas Marina Circuit , Abu Dhabi"]),
    dict(name="Korea International Circuit", location="Yeongam", country="South Korea",
         lat=34.7333, lon=126.4164,
         aliases=["Korea International Circuit , Yeongam"]),
    dict(name="Buddh International Circuit", location="Greater Noida", country="India",
         lat=28.3486, lon=77.5331,
         aliases=["Buddh International Circuit , Greater Noida"]),
    dict(name="Circuit of the Americas", location="Austin, Texas", country="United States",
         lat=30.1328, lon=-97.6411,
         aliases=["Circuit of the Americas , Austin, Texas",
                  "Circuit of the Americas , Austin , Texas"]),
    dict(name="Sochi Autodrom", location="Sochi", country="Russia",
         lat=43.4057, lon=39.9578,
         aliases=["Sochi Autodrom , Sochi"]),
    dict(name="Autódromo Hermanos Rodríguez", location="Mexico City", country="Mexico",
         lat=19.4042, lon=-99.0907,
         aliases=["Autódromo Hermanos Rodríguez , Mexico City"]),
    dict(name="Baku City Circuit", location="Baku", country="Azerbaijan",
         lat=40.3725, lon=49.8533,
         aliases=["Baku City Circuit , Baku"]),
    dict(name="Circuit Paul Ricard", location="Le Castellet", country="France",
         lat=43.2506, lon=5.7917,
         aliases=["Circuit Paul Ricard , Le Castellet"]),
    dict(name="Autodromo Internazionale del Mugello", location="Scarperia e San Piero", country="Italy",
         lat=43.9975, lon=11.3719,
         aliases=["Autodromo Internazionale del Mugello , Scarperia e San Piero"]),
    dict(name="Autódromo Internacional do Algarve", location="Portimão", country="Portugal",
         lat=37.2306, lon=-8.6267,
         aliases=["Autódromo Internacional do Algarve , Portimão",
                  "Algarve International Circuit , Portimão"]),
    dict(name="Circuit Zandvoort", location="Zandvoort", country="Netherlands",
         lat=52.3888, lon=4.5409,
         aliases=["Circuit Zandvoort , Zandvoort"]),
    dict(name="Lusail International Circuit", location="Lusail", country="Qatar",
         lat=25.4886, lon=51.4525,
         aliases=["Lusail International Circuit , Lusail"]),
    dict(name="Jeddah Corniche Circuit", location="Jeddah", country="Saudi Arabia",
         lat=21.6319, lon=39.1044,
         aliases=["Jeddah Corniche Circuit , Jeddah"]),
    dict(name="Miami International Autodrome", location="Miami Gardens, Florida", country="United States",
         lat=25.9581, lon=-80.2389,
         aliases=["Miami International Autodrome , Miami Gardens, Florida"]),
    dict(name="Las Vegas Strip Circuit", location="Paradise, Nevada", country="United States",
         lat=36.1147, lon=-115.1728,
         aliases=["Las Vegas Strip Circuit , Paradise, Nevada"]),
    # Circuit neuf (calendrier 2026) : coordonnées à confirmer.
    dict(name="Madring", location="Madrid", country="Spain",
         lat=40.4200, lon=-3.7100,
         aliases=["Madring , Madrid"]),
]


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return "-".join(ascii_name.lower().split())


def load_raw_circuits() -> set[str]:
    with open(CALENDARS_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return {
            row["Circuit"]
            for row in reader
            if row["Circuit"].strip() and not row["Round"].strip().startswith("Source")
        }


def main() -> None:
    raw_circuits = load_raw_circuits()
    known_aliases: set[str] = set()
    for circuit in CIRCUITS:
        known_aliases.update(circuit["aliases"])

    missing = raw_circuits - known_aliases
    if missing:
        print("Libellés bruts non couverts par CIRCUITS :", file=sys.stderr)
        for m in sorted(missing):
            print(f"  {m!r}", file=sys.stderr)
        sys.exit(1)

    unused = known_aliases - raw_circuits
    if unused:
        print("Alias déclarés mais absents de f1_calendars.csv :", file=sys.stderr)
        for u in sorted(unused):
            print(f"  {u!r}", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["circuit_id", "name", "location", "country", "latitude", "longitude", "aliases"])
        for circuit in sorted(CIRCUITS, key=lambda c: (c["country"], c["name"])):
            writer.writerow([
                slugify(circuit["name"]),
                circuit["name"],
                circuit["location"],
                circuit["country"],
                circuit["lat"],
                circuit["lon"],
                ";".join(circuit["aliases"]),
            ])

    print(f"OK — {len(CIRCUITS)} circuits écrits dans {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
