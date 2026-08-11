#!/usr/bin/env python3
"""
Scrape les tableaux "Calendar" des pages Wikipedia (anglais) des saisons F1
(ex: https://en.wikipedia.org/wiki/2003_Formula_One_World_Championship)
pour les années données, et exporte tout dans un seul fichier CSV avec
une colonne "Year" pour distinguer chaque saison.

Dépendances :
    pip install requests beautifulsoup4 pandas lxml

Usage :
    python scrape_f1_calendars.py
    python scrape_f1_calendars.py --start 2000 --end 2026 --output f1_calendars.csv
"""

import argparse
import re
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    # Wikipedia demande un User-Agent identifiable, sinon ça peut bloquer.
    "User-Agent": "F1CalendarScraper/1.0 (personal script; contact: none)"
}

WIKI_URL_TEMPLATE = "https://en.wikipedia.org/wiki/{year}_Formula_One_World_Championship"

# Certaines très anciennes saisons ont un titre de page différent, on gère
# les cas particuliers ici si besoin (aucun cas connu entre 2000 et 2026,
# mais on garde la structure ouverte).
URL_OVERRIDES = {}


def get_page_html(year: int) -> str:
    url = URL_OVERRIDES.get(year, WIKI_URL_TEMPLATE.format(year=year))
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


WIKI_BASE = "https://en.wikipedia.org"


def clean_cell(cell) -> str:
    """Nettoie le texte d'une cellule de tableau : enlève les notes de bas de
    page [1], les espaces multiples, les caractères invisibles, etc."""
    # Supprime les balises <sup> (notes de bas de page)
    for sup in cell.find_all("sup"):
        sup.decompose()
    text = cell.get_text(separator=" ", strip=True)
    text = re.sub(r"\[\d+\]", "", text)          # au cas où il en resterait
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_cell_link(cell):
    """Renvoie l'URL Wikipedia absolue du premier lien pertinent (vers un
    article, pas une note de bas de page) trouvé dans la cellule, ou None."""
    for a in cell.find_all("a"):
        href = a.get("href", "")
        if href.startswith("/wiki/") and not href.startswith("/wiki/File:"):
            return WIKI_BASE + href
    return None


def find_calendar_table(soup: BeautifulSoup):
    """Trouve le tableau de calendrier de la saison.

    Stratégie :
    1. Chercher un titre de section (h2/h3) contenant 'Calendar' (ou parfois
       'Schedule' selon les années), puis prendre le premier <table> qui suit.
    2. En repli, prendre le premier tableau 'wikitable' qui a une colonne
       'Round' et une colonne 'Grand Prix' dans son en-tête.
    """
    # Stratégie 1 : via le titre de section
    heading = None
    for tag in soup.find_all(["h2", "h3"]):
        heading_text = tag.get_text(strip=True).lower()
        if "calendar" in heading_text or "schedule" in heading_text:
            heading = tag
            break

    if heading is not None:
        node = heading
        while node is not None:
            node = node.find_next(["table", "h2", "h3"])
            if node is None:
                break
            if node.name == "table":
                headers_text = " ".join(
                    th.get_text(strip=True).lower() for th in node.find_all("th")
                )
                if "round" in headers_text and (
                    "grand prix" in headers_text or "race" in headers_text
                ):
                    return node
            elif node.name in ("h2", "h3"):
                # On est sorti de la section Calendar sans trouver de table
                break

    # Stratégie 2 (repli) : scanner tous les wikitables
    for table in soup.find_all("table", class_="wikitable"):
        headers_text = " ".join(
            th.get_text(strip=True).lower() for th in table.find_all("th")
        )
        if "round" in headers_text and "circuit" in headers_text:
            return table

    return None


def parse_calendar_table(table, year: int) -> pd.DataFrame:
    rows = table.find_all("tr")

    # Récupère les en-têtes de colonnes (première ligne avec des <th>)
    header_cells = rows[0].find_all(["th", "td"])
    raw_headers = [clean_cell(c) for c in header_cells]

    records = []       # texte des cellules
    link_records = []  # lien (href) associé, si présent
    # rowspan tracking : certaines colonnes (ex: 'Round' pour les week-ends
    # sprint, ou 'Date' fusionnée) utilisent rowspan. On gère ça proprement.
    active_rowspans = {}  # col_index -> (remaining_rows, value, href)

    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        row_values = {}
        row_links = {}
        col_index = 0
        cell_iter = iter(cells)

        # d'abord on comble les colonnes encore actives par rowspan
        max_cols = len(raw_headers)
        while col_index < max_cols:
            if col_index in active_rowspans:
                remaining, value, href = active_rowspans[col_index]
                row_values[col_index] = value
                row_links[col_index] = href
                remaining -= 1
                if remaining <= 0:
                    del active_rowspans[col_index]
                else:
                    active_rowspans[col_index] = (remaining, value, href)
                col_index += 1
                continue

            try:
                cell = next(cell_iter)
            except StopIteration:
                break

            value = clean_cell(cell)
            href = get_cell_link(cell)
            rowspan = int(cell.get("rowspan", 1))
            row_values[col_index] = value
            row_links[col_index] = href
            if rowspan > 1:
                active_rowspans[col_index] = (rowspan - 1, value, href)
            col_index += 1

        if not row_values:
            continue

        records.append(row_values)
        link_records.append(row_links)

    df = pd.DataFrame.from_records(records)
    links_df = pd.DataFrame.from_records(link_records)
    # Renomme les colonnes selon les en-têtes récupérés (tronqué à la taille réelle)
    col_names = raw_headers[: df.shape[1]] if raw_headers else list(df.columns)
    df.columns = col_names
    links_df.columns = col_names[: links_df.shape[1]]

    # Sélection/renommage des colonnes qui nous intéressent : Round, Grand Prix,
    # Circuit, Date. Les noms exacts varient parfois légèrement selon les années.
    # On ne mappe qu'UNE seule colonne source par nom cible, pour éviter de
    # générer des colonnes dupliquées (ex: 'Date' et 'Race date' présentes
    # toutes les deux, ou colonnes fusionnées mal alignées).
    rename_map = {}
    used_targets = set()

    def assign(col, target):
        if target in used_targets:
            return
        rename_map[col] = target
        used_targets.add(target)

    for col in df.columns:
        col_lower = str(col).lower()
        if col_lower.startswith("round"):
            assign(col, "Round")
        elif "grand prix" in col_lower or col_lower.startswith("race"):
            assign(col, "Grand Prix")
        elif "circuit" in col_lower:
            assign(col, "Circuit")
        elif "date" in col_lower:
            # Gère 'Date', 'Race date', 'Date(s)', etc. (le libellé varie
            # selon les années — ex: 2026 utilise 'Race date').
            assign(col, "Date")

    # Récupère le lien de la colonne source qui a été mappée vers 'Circuit',
    # AVANT le renommage, pour retrouver la bonne colonne dans links_df.
    circuit_source_col = next((c for c, t in rename_map.items() if t == "Circuit"), None)
    if circuit_source_col is not None and circuit_source_col in links_df.columns:
        circuit_urls = links_df[circuit_source_col]
    else:
        circuit_urls = pd.Series([None] * len(df))

    df = df.rename(columns=rename_map)

    keep_cols = [c for c in ["Round", "Grand Prix", "Circuit", "Date"] if c in df.columns]
    df = df.loc[:, keep_cols]
    # Sécurité supplémentaire : si jamais des doublons subsistent malgré
    # tout (ex. table mal formée), on ne garde que la première occurrence
    # de chaque colonne.
    df = df.loc[:, ~df.columns.duplicated()]

    if "Circuit" in df.columns:
        circuit_pos = df.columns.get_loc("Circuit") + 1
        df.insert(circuit_pos, "Circuit URL", circuit_urls.reset_index(drop=True))

    # Enlève d'éventuelles lignes "Source" / notes en bas de tableau
    if "Round" in df.columns:
        df = df[df["Round"].astype(str).str.strip() != ""]

    df.insert(0, "Year", year)
    return df.reset_index(drop=True)


def scrape_year(year: int) -> pd.DataFrame | None:
    try:
        html = get_page_html(year)
    except requests.RequestException as e:
        print(f"[{year}] Erreur de téléchargement : {e}", file=sys.stderr)
        return None

    soup = BeautifulSoup(html, "lxml")
    table = find_calendar_table(soup)
    if table is None:
        print(f"[{year}] Tableau 'Calendar' introuvable, saison ignorée.", file=sys.stderr)
        return None

    try:
        df = parse_calendar_table(table, year)
    except Exception as e:
        print(f"[{year}] Erreur de parsing : {e}", file=sys.stderr)
        return None

    if df.empty:
        print(f"[{year}] Tableau vide après parsing, saison ignorée.", file=sys.stderr)
        return None

    print(f"[{year}] OK — {len(df)} courses récupérées.")
    return df


def main():
    parser = argparse.ArgumentParser(description="Scrape les calendriers F1 Wikipedia.")
    parser.add_argument("--start", type=int, default=2000, help="Année de début (incluse)")
    parser.add_argument("--end", type=int, default=2026, help="Année de fin (incluse)")
    parser.add_argument("--output", type=str, default="f1_calendars.csv", help="Fichier CSV de sortie")
    parser.add_argument("--delay", type=float, default=1.0, help="Délai (s) entre requêtes, pour être poli avec Wikipedia")
    args = parser.parse_args()

    all_dfs = []
    for year in range(args.start, args.end + 1):
        df = scrape_year(year)
        if df is not None:
            all_dfs.append(df)
        time.sleep(args.delay)

    if not all_dfs:
        print("Aucune donnée récupérée, arrêt.", file=sys.stderr)
        sys.exit(1)

    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"\nTerminé : {len(final_df)} lignes écrites dans {args.output}")


if __name__ == "__main__":
    main()