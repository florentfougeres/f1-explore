import { Map, NavigationControl, Popup, LngLatBounds } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
const SOURCE_ID = "season-races";
const ROUTE_SOURCE_ID = "season-route";

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

function toRouteGeoJSON(races) {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: races.map((r) => [r.lon, r.lat]),
        },
        properties: {},
      },
    ],
  };
}

function setupLayers() {
  map.addSource(ROUTE_SOURCE_ID, { type: "geojson", data: toRouteGeoJSON([]) });
  map.addLayer({
    id: "route-line",
    type: "line",
    source: ROUTE_SOURCE_ID,
    paint: {
      "line-color": "#e10600",
      "line-width": 1.5,
      "line-dasharray": [2, 2],
      "line-opacity": 0.55,
    },
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
  document.querySelectorAll("#race-list li.selected").forEach((li) => li.classList.remove("selected"));
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

  if (fly) {
    map.flyTo({ center: [race.lon, race.lat], zoom: 6, speed: 0.9, curve: 1.3 });
  }

  if (openPopup) {
    const tpl = document.getElementById("popup-template");
    const node = tpl.cloneNode(true);
    node.hidden = false;
    node.removeAttribute("id");
    node.querySelector(".popup-round").textContent = `Round ${race.round}`;
    node.querySelector(".popup-gp").textContent = race.grand_prix;
    node.querySelector(".popup-circuit").textContent = `${race.name} — ${race.location}, ${race.country}`;
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
  map.getSource(ROUTE_SOURCE_ID).setData(toRouteGeoJSON(currentRaces));

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
  const res = await fetch("/data/seasons.json");
  seasons = await res.json();
  years = Object.keys(seasons).sort((a, b) => Number(a) - Number(b));
  seasonSlider.max = years.length - 1;

  await new Promise((resolve) => map.on("load", resolve));
  setupLayers();
  renderSeason(years[years.length - 1]);
}

init();
