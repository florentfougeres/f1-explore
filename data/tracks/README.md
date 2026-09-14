# Tracés des circuits

Géométries (`LineString`) des tracés officiels, une par circuit, fichier
nommé `<circuit_id>.geojson` (même `circuit_id` que `data/circuits.csv`).

**Source** : [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits)
(MIT, voir `LICENSE-f1-circuits.md`), vendorisé ici (35/39 circuits) plutôt
que refetché à chaque build.

4 circuits de `data/circuits.csv` n'ont pas de tracé disponible dans cette
source (venues de courte durée sur des années non couvertes par le jeu de
données) : Fuji Speedway, Valencia Street Circuit, Korea International
Circuit, Buddh International Circuit. La web app se contente du marqueur
pour ceux-là.
