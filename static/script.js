function initializePinmap() {
const STORAGE_KEYS = {
  pins: "pinmap:pins",
};

const fallbackCenter = [-14.235, -51.9253];
const i18n = window.pinmapI18n;
const t = i18n?.t ?? ((key) => key);

function initMap() {
  const mapElement = document.querySelector("#map");

  if (!mapElement || typeof L === "undefined") {
    console.error("Nao foi possivel iniciar o mapa: container #map ou Leaflet indisponivel.");
    return null;
  }

  const map = L.map("map", {
    attributionControl: true,
    maxZoom: 18,
    minZoom: 2,
    worldCopyJump: true,
    zoomControl: true,
  }).setView(fallbackCenter, 4);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    detectRetina: false,
    keepBuffer: 2,
    maxNativeZoom: 18,
    maxZoom: 18,
    updateWhenIdle: true,
    updateWhenZooming: false,
  }).addTo(map);

  const markerLayer = L.layerGroup().addTo(map);

  function invalidateMapSize() {
    map.invalidateSize();
  }

  requestAnimationFrame(() => {
    requestAnimationFrame(invalidateMapSize);
  });

  setTimeout(invalidateMapSize, 600);
  setTimeout(invalidateMapSize, 900);

  let resizeTimer;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(invalidateMapSize, 150);
  });

  map.whenReady(() => {
    setTimeout(invalidateMapSize, 600);
  });

  return { map, markerLayer, invalidateMapSize };
}

const mapState = initMap();
if (!mapState) {
  return;
}

const { map, markerLayer, invalidateMapSize } = mapState;

const visitCount = document.querySelector("#visitCount");
const visitLabel = document.querySelector("#visitLabel");
const pinForm = document.querySelector("#pinForm");
const pinList = document.querySelector("#pinList");
const locateButton = document.querySelector("#locateButton");
const pinItemTemplate = document.querySelector("#pinItemTemplate");
const latitudeInput = document.querySelector("#latitude");
const longitudeInput = document.querySelector("#longitude");
const languageSelect = document.querySelector("#languageSelect");

let draftMarker;
let currentPins = [];
let backendAvailable = false;

function loadPins() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.pins)) ?? [];
  } catch {
    return [];
  }
}

function savePins(pins) {
  localStorage.setItem(STORAGE_KEYS.pins, JSON.stringify(pins));
}

async function loadBackendPins() {
  const response = await fetch("/api/pins");

  if (!response.ok) {
    throw new Error(t("error.backendLoad"));
  }

  return response.json();
}

async function saveBackendPin(pin) {
  const response = await fetch("/api/pins", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: pin.name,
      origin: pin.origin,
      lat: pin.lat,
      lng: pin.lng,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(data.error || t("error.backendSave"));
    error.code = data.code;
    error.status = response.status;
    throw error;
  }

  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  return new Intl.DateTimeFormat(i18n?.getSavedLanguage?.() ?? "pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

async function refreshVisitCounter() {
  visitLabel.textContent = t("counter.label");

  try {
    const response = await fetch("/api/visits");
    if (!response.ok) {
      throw new Error("Could not load visit counter.");
    }

    const data = await response.json();
    visitCount.textContent = Number(data.visits || 0);
  } catch (error) {
    console.error(error);
    visitCount.textContent = "0";
  }
}

function updateDraftMarker(lat, lng) {
  latitudeInput.value = lat.toFixed(6);
  longitudeInput.value = lng.toFixed(6);

  if (!draftMarker) {
    draftMarker = L.marker([lat, lng], { draggable: true }).addTo(map);
    draftMarker.on("dragend", () => {
      const position = draftMarker.getLatLng();
      updateDraftMarker(position.lat, position.lng);
    });
    return;
  }

  draftMarker.setLatLng([lat, lng]);
}

function renderPins(pins = currentPins) {
  currentPins = pins;
  markerLayer.clearLayers();
  pinList.replaceChildren();

  pins.forEach((pin) => {
    const hasCustomName = pin.name && pin.name !== "Visitante anonimo";
    const nameLine = hasCustomName ? `<span>${escapeHtml(pin.name)}</span>` : "";
    const popup = `
      <article class="pin-popup">
        <strong>${escapeHtml(pin.origin)}</strong>
        ${nameLine}
        <time datetime="${escapeHtml(pin.createdAt)}">${formatDate(pin.createdAt)}</time>
      </article>
    `;

    L.marker([pin.lat, pin.lng], { title: pin.origin }).bindPopup(popup).addTo(markerLayer);

    const item = pinItemTemplate.content.firstElementChild.cloneNode(true);
    item.querySelector("strong").textContent = pin.origin;
    item.querySelector("span").textContent = hasCustomName ? pin.name : "";
    item.querySelector("span").hidden = !hasCustomName;
    item.querySelector("time").dateTime = pin.createdAt;
    item.querySelector("time").textContent = formatDate(pin.createdAt);
    pinList.append(item);
  });

  if (pins.length === 0) {
    const emptyItem = document.createElement("li");
    emptyItem.textContent = t("pins.empty");
    pinList.append(emptyItem);
  }

  setTimeout(invalidateMapSize, 100);
}

async function refreshPins() {
  try {
    currentPins = await loadBackendPins();
    backendAvailable = true;
    renderPins();
  } catch (error) {
    console.error(error);
    backendAvailable = false;
    currentPins = loadPins();
    renderPins();
  }
}

function getCleanValue(formData, key, fallback = "") {
  return String(formData.get(key) || fallback).trim();
}

map.on("click", (event) => {
  updateDraftMarker(event.latlng.lat, event.latlng.lng);
});

if (i18n && languageSelect) {
  languageSelect.value = i18n.getSavedLanguage();
  document.documentElement.lang = i18n.getSavedLanguage();
  i18n.translatePage();
  languageSelect.addEventListener("change", () => {
    i18n.setLanguage(languageSelect.value);
  });
  window.addEventListener("pinmap:languagechange", () => {
    visitLabel.textContent = t("counter.label");
    renderPins();
  });
}

locateButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    alert(t("error.geolocation.unsupported"));
    return;
  }

  locateButton.disabled = true;
  locateButton.textContent = t("form.locating");

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      map.setView([latitude, longitude], 10);
      updateDraftMarker(latitude, longitude);
      locateButton.disabled = false;
      locateButton.textContent = t("form.locate");
    },
    () => {
      alert(t("error.geolocation.failed"));
      locateButton.disabled = false;
      locateButton.textContent = t("form.locate");
    },
    { enableHighAccuracy: true, timeout: 9000 }
  );
});

pinForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(pinForm);
  const lat = Number(getCleanValue(formData, "latitude"));
  const lng = Number(getCleanValue(formData, "longitude"));

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    alert(t("error.invalidPin"));
    return;
  }

  const name = getCleanValue(formData, "visitorName", "Visitante anonimo") || "Visitante anonimo";
  const origin = getCleanValue(formData, "origin");

  const pin = {
    id: crypto.randomUUID(),
    name,
    origin,
    lat,
    lng,
    createdAt: new Date().toISOString(),
  };

  try {
    await saveBackendPin(pin);
    await refreshPins();
  } catch (error) {
    console.error(error);

    if (error.status >= 400 && error.status < 500) {
      const errorKeyByCode = {
        blocked_origin: "error.blockedOrigin",
        invalid_coordinates: "error.invalidCoordinates",
        invalid_origin: "error.invalidOrigin",
      };
      const messageKey = error.status === 429
        ? "error.rateLimited"
        : errorKeyByCode[error.code] || "error.backendRejected";
      alert(t(messageKey));
      return;
    }

    const pins = [pin, ...loadPins()].slice(0, 100);
    savePins(pins);
    renderPins(pins);
    backendAvailable = false;
    alert(t("error.backendFallback"));
  }

  pinForm.reset();

  if (draftMarker) {
    draftMarker.remove();
    draftMarker = null;
  }
});

refreshVisitCounter();
setTimeout(refreshPins, 700);
}

if (document.readyState === "complete") {
  initializePinmap();
} else {
  window.addEventListener("load", initializePinmap, { once: true });
}
