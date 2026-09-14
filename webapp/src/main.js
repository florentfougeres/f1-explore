import { Map, NavigationControl, Popup, LngLatBounds, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";

// new URL(...) dynamique dans maplibre-gl : Vite ne peut pas le bundler,
// on pointe donc explicitement vers la copie générée par
// scripts/copy-maplibre-worker.mjs (voir predev/prebuild).
setWorkerUrl(`${import.meta.env.BASE_URL}maplibre-gl-worker.mjs`);

const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
const SOURCE_ID = "season-races";
const TRACK_SOURCE_ID = "circuit-track";
const EMPTY_TRACK = { type: "FeatureCollection", features: [] };

const map = new Map({
  container: "map",
  style: MAP_STYLE,
  center: [10, 25],
  zoom: 1.6,
  attributionControl: { compact: true },
});
map.addControl(new NavigationControl({ showCompass: false }), "bottom-right");

const panel = document.getElementById("panel");
const panelToggle = document.getElementById("panel-toggle");
const seasonSlider = document.getElementById("season-slider");
const seasonYearEl = document.getElementById("season-year");
const seasonMetaEl = document.getElementById("season-meta");
const prevBtn = document.getElementById("prev-season");
const nextBtn = document.getElementById("next-season");
const raceListEl = document.getElementById("race-list");
const playBtn = document.getElementById("play-btn");

panelToggle.addEventListener("click", () => panel.classList.toggle("collapsed"));

let seasons = {};
let years = [];
let tracksByCircuitId = {};
let currentYear = null;
let currentRaces = [];
let selectedRound = null;
let popup = null;
let playing = false;
let playToken = 0;

function toGeoJSON(races) {
  return {
    type: "FeatureCollection",
    features: races.map((race) => ({
      type: "Feature",
      id: race.round,
      geometry: { type: "Point", coordinates: [race.lon, race.lat] },
      properties: { ...race },
    })),
  };
}

function setupLayers() {
  map.addSource(TRACK_SOURCE_ID, { type: "geojson", data: EMPTY_TRACK });
  map.addLayer({
    id: "track-casing",
    type: "line",
    source: TRACK_SOURCE_ID,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: { "line-color": "#ffffff", "line-width": 6, "line-opacity": 0.9 },
  });
  map.addLayer({
    id: "track-line",
    type: "line",
    source: TRACK_SOURCE_ID,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: { "line-color": "#e10600", "line-width": 3 },
  });

  map.addSource(SOURCE_ID, { type: "geojson", data: toGeoJSON([]) });

  map.addLayer({
    id: "circuit-glow",
    type: "circle",
    source: SOURCE_ID,
    paint: {
      "circle-radius": ["case", ["boolean", ["feature-state", "selected"], false], 22, 0],
      "circle-color": "#e10600",
      "circle-opacity": 0.18,
      "circle-blur": 1,
    },
  });

  map.addLayer({
    id: "circuit-dots",
    type: "circle",
    source: SOURCE_ID,
    paint: {
      "circle-radius": ["case", ["boolean", ["feature-state", "selected"], false], 10, 7],
      "circle-color": ["case", ["boolean", ["feature-state", "selected"], false], "#e10600", "#ffffff"],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#e10600",
    },
  });

  map.addLayer({
    id: "circuit-labels",
    type: "symbol",
    source: SOURCE_ID,
    layout: {
      "text-field": ["get", "round"],
      "text-size": 10,
      "text-font": ["Noto Sans Bold"],
    },
    paint: {
      "text-color": ["case", ["boolean", ["feature-state", "selected"], false], "#ffffff", "#e10600"],
    },
  });

  map.on("mouseenter", "circuit-dots", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "circuit-dots", () => (map.getCanvas().style.cursor = ""));

  map.on("click", "circuit-dots", (e) => {
    const round = e.features[0].properties.round;
    selectRace(round, { fly: true, openPopup: true });
  });
}

function clearSelection() {
  if (selectedRound !== null) {
    try {
      map.setFeatureState({ source: SOURCE_ID, id: selectedRound }, { selected: false });
    } catch {
      /* source may not have this feature anymore */
    }
  }
  selectedRound = null;
  if (popup) {
    popup.remove();
    popup = null;
  }
  map.getSource(TRACK_SOURCE_ID)?.setData(EMPTY_TRACK);
  document.querySelectorAll("#race-list li.selected").forEach((li) => li.classList.remove("selected"));
}

function trackBounds(feature) {
  const coords = feature.geometry.coordinates;
  return coords.reduce((b, c) => b.extend(c), new LngLatBounds(coords[0], coords[0]));
}

function selectRace(round, { fly = false, openPopup = false } = {}) {
  const race = currentRaces.find((r) => r.round === round);
  if (!race) return;

  clearSelection();
  selectedRound = round;
  map.setFeatureState({ source: SOURCE_ID, id: round }, { selected: true });

  const li = raceListEl.querySelector(`li[data-round="${round}"]`);
  if (li) {
    li.classList.add("selected");
    li.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  const track = tracksByCircuitId[race.circuit_id];
  map.getSource(TRACK_SOURCE_ID)?.setData(track ? { type: "FeatureCollection", features: [track] } : EMPTY_TRACK);

  if (fly) {
    if (track) {
      map.fitBounds(trackBounds(track), { padding: 90, maxZoom: 17, duration: 1200 });
    } else {
      map.flyTo({ center: [race.lon, race.lat], zoom: 15, speed: 0.9, curve: 1.3 });
    }
  }

  if (openPopup) {
    const tpl = document.getElementById("popup-template");
    const node = tpl.cloneNode(true);
    node.hidden = false;
    node.removeAttribute("id");
    node.querySelector(".popup-round").textContent = `Round ${race.round}`;
    node.querySelector(".popup-gp").textContent = race.grand_prix;
    const lengthKm = track?.properties?.length ? ` · ${(track.properties.length / 1000).toFixed(3)} km` : "";
    node.querySelector(".popup-circuit").textContent = `${race.name} — ${race.location}, ${race.country}${lengthKm}`;
    node.querySelector(".popup-date").textContent = race.date ? `${race.date} ${currentYear}` : currentYear;

    popup = new Popup({ closeOnClick: false, offset: 14 })
      .setLngLat([race.lon, race.lat])
      .setDOMContent(node)
      .addTo(map);
    popup.on("close", () => {
      if (selectedRound === round) clearSelection();
    });
  }
}

function renderRaceList(races) {
  raceListEl.innerHTML = "";
  for (const race of races) {
    const li = document.createElement("li");
    li.dataset.round = race.round;
    li.innerHTML = `
      <span class="race-round">${race.round}</span>
      <span class="race-info">
        <span class="race-gp">${race.grand_prix}</span>
        <span class="race-sub">${race.date ? `${race.name} · ${race.date}` : race.name}</span>
      </span>
    `;
    li.addEventListener("click", () => selectRace(race.round, { fly: true, openPopup: true }));
    raceListEl.appendChild(li);
  }
}

function fitToRaces(races) {
  if (!races.length) return;
  const bounds = races.reduce(
    (b, r) => b.extend([r.lon, r.lat]),
    new LngLatBounds([races[0].lon, races[0].lat], [races[0].lon, races[0].lat])
  );
  map.fitBounds(bounds, { padding: { top: 80, bottom: 80, left: 400, right: 80 }, maxZoom: 5, duration: 900 });
}

function renderSeason(year) {
  currentYear = year;
  currentRaces = seasons[year];
  stopPlayback();
  clearSelection();

  seasonYearEl.textContent = year;
  seasonMetaEl.textContent = `${currentRaces.length} courses`;
  seasonSlider.value = years.indexOf(year);

  map.getSource(SOURCE_ID).setData(toGeoJSON(currentRaces));

  renderRaceList(currentRaces);
  fitToRaces(currentRaces);
}

function stopPlayback() {
  playing = false;
  playToken += 1;
  playBtn.textContent = "▶ Parcourir la saison";
  playBtn.classList.remove("playing");
}

async function playSeason() {
  if (playing) {
    stopPlayback();
    return;
  }
  playing = true;
  const token = ++playToken;
  playBtn.textContent = "⏸ Arrêter";
  playBtn.classList.add("playing");

  for (const race of currentRaces) {
    if (token !== playToken) return;
    selectRace(race.round, { fly: true, openPopup: true });
    await new Promise((resolve) => setTimeout(resolve, 2600));
  }
  if (token === playToken) stopPlayback();
}

playBtn.addEventListener("click", playSeason);
prevBtn.addEventListener("click", () => {
  const i = years.indexOf(currentYear);
  if (i > 0) renderSeason(years[i - 1]);
});
nextBtn.addEventListener("click", () => {
  const i = years.indexOf(currentYear);
  if (i < years.length - 1) renderSeason(years[i + 1]);
});
seasonSlider.addEventListener("input", (e) => {
  renderSeason(years[Number(e.target.value)]);
});

async function init() {
  const [seasonsRes, tracksRes] = await Promise.all([
    fetch(`${import.meta.env.BASE_URL}data/seasons.json`),
    fetch(`${import.meta.env.BASE_URL}data/tracks.geojson`),
  ]);
  seasons = await seasonsRes.json();
  years = Object.keys(seasons).sort((a, b) => Number(a) - Number(b));
  seasonSlider.max = years.length - 1;

  const tracksFC = await tracksRes.json();
  tracksByCircuitId = Object.fromEntries(
    tracksFC.features.map((f) => [f.properties.circuit_id, f])
  );

  await new Promise((resolve) => map.on("load", resolve));
  setupLayers();
  renderSeason(years[years.length - 1]);
}

init();
