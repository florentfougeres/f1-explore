# F1 Explorer

Web app MapLibre GL pour explorer les circuits F1 saison par saison
(2000-2026), à partir des données de `../data/f1_calendars.csv` et
`../data/circuits.csv`.

## Lancer en dev

```bash
npm install
npm run dev
```

## Build de prod

```bash
npm run build
npm run preview
```

## Régénérer les données

Le fichier `public/data/seasons.json` est généré depuis les CSV du dépôt :

```bash
python3 ../scripts/build_webapp_data.py
```

À relancer après toute modification de `data/f1_calendars.csv` ou
`data/circuits.csv`.

## Notes

- Fond de carte : [OpenFreeMap](https://openfreemap.org/) (style "positron",
  gratuit, sans clé API).
- Les coordonnées des circuits (`data/circuits.csv`) sont approximatives —
  à vérifier avant tout usage nécessitant une précision cartographique fine.
- Certaines saisons (2021-2026) n'ont pas de date de course dans les
  données sources (gap du scraper Wikipedia, cf. `data/f1_calendars.csv`) ;
  l'UI masque simplement la date quand elle est absente.
