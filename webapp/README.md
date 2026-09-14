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

## Déploiement GitHub Pages

Le workflow `.github/workflows/deploy-pages.yml` build et déploie
automatiquement sur push vers `main` (ou déclenchement manuel depuis
l'onglet Actions). Il régénère `seasons.json`, build l'app avec
`base: "/f1-explore/"` (voir `vite.config.js`), et publie `dist/`.

**Étape unique à faire manuellement** dans le repo GitHub : Settings →
Pages → Source → "GitHub Actions" (au lieu de "Deploy from a branch").
Une fois fait, l'app est servie sur `https://<owner>.github.io/f1-explore/`.

## Notes

- Fond de carte : [OpenFreeMap](https://openfreemap.org/) (style "positron",
  gratuit, sans clé API).
- Les coordonnées des circuits (`data/circuits.csv`) sont approximatives —
  à vérifier avant tout usage nécessitant une précision cartographique fine.
- Certaines saisons (2021-2026) n'ont pas de date de course dans les
  données sources (gap du scraper Wikipedia, cf. `data/f1_calendars.csv`) ;
  l'UI masque simplement la date quand elle est absente.
