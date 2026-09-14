// MapLibre GL charge son worker via une URL construite dynamiquement
// (new URL(`./${name}`, base)) que Vite ne peut pas analyser statiquement,
// donc ces fichiers ne sont jamais inclus dans le bundle automatiquement.
// maplibre-gl-worker.mjs importe à son tour maplibre-gl-shared.mjs en
// relatif : les deux doivent être copiés côte à côte. On les régénère
// depuis node_modules à chaque dev/build, et setWorkerUrl() (dans
// src/main.js) pointe explicitement vers la copie du worker.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const srcDir = join(root, "node_modules/maplibre-gl/dist");
const destDir = join(root, "public");

mkdirSync(destDir, { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(srcDir, file), join(destDir, file));
  console.log(`Copié ${file} vers ${destDir}`);
}
