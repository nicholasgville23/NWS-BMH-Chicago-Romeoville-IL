"use strict";

const LAST_MAP_UPDATE = "Tue, Aug 11, 2026 at 8:00:27 pm CDT";

const ACTIVE_PRODUCTS = [
  { name: "Flood Watch", active: true },
  { name: "Hazardous Weather Outlook", active: true },
];

const NEIGHBORING_WFOS = [
  { office: "La Crosse, WI", code: "ARX", direction: "NW" },
  { office: "Milwaukee/Sullivan, WI", code: "MKX", direction: "N" },
  { office: "Grand Rapids, MI", code: "GRR", direction: "NE" },
  { office: "Quad Cities, IA/IL", code: "DVN", direction: "W" },
  { office: "Northern Indiana", code: "IWX", direction: "E" },
  { office: "St. Louis, MO", code: "LSX", direction: "SW" },
  { office: "Central Illinois", code: "ILX", direction: "S" },
  { office: "Indianapolis, IN", code: "IND", direction: "SE" },
];

const ZOOM_OUT = { label: "Zoom Out", direction: "center" };

function renderWfoLotMap(containerId) {
  const container = typeof containerId === "string" ? document.getElementById(containerId) : containerId;
  if (!container) {
    throw new Error("renderWfoLotMap: container not found");
  }

  container.innerHTML = "";
  const mapWrapper = document.createElement("div");
  mapWrapper.className = "wfo-lot-map-container";
  mapWrapper.style.border = "1px solid #ccc";
  mapWrapper.style.padding = "10px";
  mapWrapper.style.maxWidth = "600px";
  const title = document.createElement("h2");
  title.textContent = "NWS Chicago/Romeoville Forecast Area";
  mapWrapper.appendChild(title);

  const meta = document.createElement("p");
  meta.innerHTML = `<strong>Last Updated:</strong> ${LAST_MAP_UPDATE}`;
  mapWrapper.appendChild(meta);

  const mapImg = document.createElement("img");
  mapImg.src = "https://www.weather.gov/images/lot/forecast_area.png";
  mapImg.alt = "NWS LOT Forecast Area Map";
  mapImg.style.width = "100%";
  mapWrapper.appendChild(mapImg);
  const legend = document.createElement("div");
  legend.innerHTML = "<h3>Active Alerts</h3>";
  const pList = document.createElement("ul");
  ACTIVE_PRODUCTS.forEach(p => {
    const li = document.createElement("li");
    li.textContent = p.name;
    if(p.active) li.style.color = "red";
    pList.appendChild(li);
  });
  legend.appendChild(pList);
  mapWrapper.appendChild(legend);
  container.appendChild(mapWrapper);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { LAST_MAP_UPDATE, ACTIVE_PRODUCTS, NEIGHBORING_WFOS, ZOOM_OUT, renderWfoLotMap };
} else if (typeof window !== "undefined") {
  window.WfoLotMap = { LAST_MAP_UPDATE, ACTIVE_PRODUCTS, NEIGHBORING_WFOS, ZOOM_OUT, renderWfoLotMap };
}

/**
 * Renders the neighboring WFO navigation grid.
 * @param {HTMLElement} container - The container to append the navigation to.
 */
function renderNeighborNavigation(container) {
  const navSection = document.createElement("div");
  navSection.className = "neighboring-wfos-nav";
  navSection.style.marginTop = "20px";
  navSection.innerHTML = "<h3>Neighboring WFOs</h3>";

  const grid = document.createElement("div");
  grid.style.display = "grid";
  grid.style.gridTemplateColumns = "repeat(3, 1fr)";
  grid.style.gap = "10px";

  [...NEIGHBORING_WFOS, ZOOM_OUT].forEach(wfo => {
    const btn = document.createElement("button");
    btn.textContent = wfo.code || wfo.label;
    btn.title = wfo.office || wfo.label;
    btn.onclick = () => console.log(`Navigating to ${wfo.code || wfo.direction}`);
    grid.appendChild(btn);
  });

  navSection.appendChild(grid);
  container.appendChild(navSection);
}

// Ensure the application can initialize when the DOM is ready
if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.getElementById("app") || document.body;
    if (appContainer) {
      renderWfoLotMap(appContainer);
      renderNeighborNavigation(appContainer.querySelector(".wfo-lot-map-container"));
    }
  });
}

/**
 * Renders the full alert legend as requested by the UI specification.
 * @param {HTMLElement} container
 */
function renderAlertLegend(container) {
  const alerts = [
    "Flood Warning", "Flash Flood Watch", "Flood Advisory",
    "Flood Watch", "Hazardous Weather Outlook", "Hydrologic Outlook"
  ];

  const alertSection = document.createElement("div");
  alertSection.className = "alert-legend";
  alertSection.innerHTML = "<h3>Watches, Warnings & Advisories</h3>";

  const list = document.createElement("ul");
  alerts.forEach(alert => {
    const li = document.createElement("li");
    li.textContent = alert;
    list.appendChild(li);
  });

  alertSection.appendChild(list);
  const footer = document.createElement("p");
  footer.innerHTML = `Visit at: <a href="http://127.0.0.1:3000/wfo/lot">127.0.0.1:3000/wfo/lot</a>`;
  alertSection.appendChild(footer);

  container.appendChild(alertSection);
}

// Update the DOMContentLoaded listener to include the new legend
if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.getElementById("app") || document.body;
    if (appContainer) {
      renderWfoLotMap(appContainer);
      const mapContainer = appContainer.querySelector(".wfo-lot-map-container");
      if (mapContainer) {
        renderNeighborNavigation(mapContainer);
        renderAlertLegend(mapContainer);
      }
    }
  });
}

"use strict";
const express = require('express');
const app = express();
const path = require('path');
const http = require('http').createServer(app);

// ... [Keep all existing bot logic/requires here] ...

// Add Web Interface Integration
app.use(express.static(path.join(__dirname, 'public')));

app.get('/wfo/lot', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Serve the specific wfo_lot_map data
app.get('/api/wfo/lot', (req, res) => {
  res.json({
    LAST_MAP_UPDATE: "Tue, Aug 11, 2026 at 8:00:27 pm CDT",
    ACTIVE_PRODUCTS: [
      { name: "Flood Watch", active: true },
      { name: "Hazardous Weather Outlook", active: true },
    ],
    NEIGHBORING_WFOS: [
      { office: "La Crosse, WI", code: "ARX", direction: "NW" },
      { office: "Milwaukee/Sullivan, WI", code: "MKX", direction: "N" },
      { office: "Grand Rapids, MI", code: "GRR", direction: "NE" },
      { office: "Quad Cities, IA/IL", code: "DVN", direction: "W" },
      { office: "Northern Indiana", code: "IWX", direction: "E" },
      { office: "St. Louis, MO", code: "LSX", direction: "SW" },
      { office: "Central Illinois", code: "ILX", direction: "S" },
      { office: "Indianapolis, IN", code: "IND", direction: "SE" },
    ]
  });
});

const PORT = process.env.PORT || 3000;
http.listen(PORT, () => {
  console.log(`${colors.cyan("[INFO]")} Web interface running on port ${PORT}`);
});

// ... [Rest of existing code remains unchanged] ...
