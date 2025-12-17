const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASE = isLocal ? "http://localhost:8081" : window.location.origin.replace("://app.", "://api.");
console.log("API_BASE =", API_BASE);

const state = {
  currentWeather: null,
  currentPlan: null,
  weatherHistory: [],
  planHistory: [],
  healthStatus: "checking",
  charts: { temp: null, condition: null },
  collapsedHistory: false,
  forecast: { today: [], days: [] },
};

const conditionIcon = (cond) => {
  const c = (cond || "").toLowerCase();
  if (c.includes("sun")) return "☀️";
  if (c.includes("rain")) return "🌧️";
  if (c.includes("snow")) return "❄️";
  return "☁️";
};

const planIcons = {
  Walk: "👣",
  Picnic: "🧺",
  Museum: "🏛️",
  Coffee: "☕",
  Cinema: "🎬",
  "Board games": "🎲",
  Ski: "⛷️",
  "Hot chocolate": "🍫",
};

const $ = (sel) => document.querySelector(sel);
const loader = $("#loader");
const toastEl = $("#toast");

const fmtRelative = (iso) => {
  if (!iso) return "—";
  const t = new Date(iso);
  const diff = (Date.now() - t.getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
};

const fmtFull = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

function showLoader(show) {
  loader.classList.toggle("hidden", !show);
  $("#btn-weather").disabled = show;
  $("#btn-plan").disabled = show;
}

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  setTimeout(() => toastEl.classList.add("hidden"), 3200);
}

async function fetchJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

async function fetchHealth() {
  try {
    const res = await fetchJson("/health");
    state.healthStatus = res.status === "ok" ? "ok" : "degraded";
  } catch {
    state.healthStatus = "degraded";
  }
  renderHealth();
}

async function fetchWeather(city) {
  const data = await fetchJson(`/api/weather?city=${encodeURIComponent(city)}`);
  state.currentWeather = data;
  return data;
}

async function fetchPlan(city) {
  const data = await fetchJson(`/api/plan?city=${encodeURIComponent(city)}`);
  state.currentPlan = data;
  return data;
}

async function fetchHistory() {
  const [weather, plans] = await Promise.all([
    fetchJson("/api/history/weather?limit=20"),
    fetchJson("/api/history/plans?limit=20"),
  ]);
  state.weatherHistory = weather;
  state.planHistory = plans;
}

function renderHealth() {
  const dot = $("#health-dot");
  const text = $("#health-text");
  if (state.healthStatus === "ok") {
    dot.classList.add("ok");
    dot.classList.remove("bad");
    text.textContent = "Online";
  } else {
    dot.classList.add("bad");
    dot.classList.remove("ok");
    text.textContent = "Degraded";
  }
}

function renderWeatherCard() {
  const data = state.currentWeather;
  if (!data) return;
  $("#weather-city").textContent = data.city || "—";
  $("#weather-source").textContent = data.source || "—";
  $("#weather-icon").textContent = conditionIcon(data.condition);
  $("#weather-temp").textContent = `${data.temp_c != null ? Number(data.temp_c).toFixed(1) : "—"}°C`;
  $("#weather-condition").textContent = data.condition || "—";
  $("#weather-updated").textContent = `Updated ${fmtFull(data.updated_at)}`;

   // Mock extra details derived deterministically
  const hash = Math.abs((data.city || "x").split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0) + Math.round(data.temp_c || 0));
  const wind = 5 + (hash % 25); // km/h
  const humidity = 40 + (hash % 50);
  const feels = data.temp_c != null ? (Number(data.temp_c) - 1 + ((hash % 5) / 10)).toFixed(1) : "—";
  $("#detail-wind").textContent = `${wind} km/h`;
  $("#detail-humidity").textContent = `${humidity}%`;
  $("#detail-feels").textContent = `${feels}°C`;
}

function renderPlanCard() {
  const data = state.currentPlan;
  const wrap = $("#plan-activities");
  wrap.innerHTML = "";
  if (!data || !data.activities) {
    wrap.innerHTML = `<span class="muted tiny">No plan yet</span>`;
    return;
  }
  $("#plan-source").textContent = data.weather_source || "—";
  data.activities.forEach((act) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.innerHTML = `<span>${planIcons[act] || "•"}</span><span>${act}</span>`;
    wrap.append(chip);
  });
  $("#plan-generated").textContent = `Generated ${fmtFull(data.generated_at)}`;
}

function renderHistoryLists() {
  const histWeather = $("#history-weather");
  const histPlans = $("#history-plans");
  histWeather.innerHTML = "";
  histPlans.innerHTML = "";

  const weatherEmpty = !state.weatherHistory.length;
  const planEmpty = !state.planHistory.length;

  if (weatherEmpty) histWeather.innerHTML = `<div class="muted">Not enough data yet.</div>`;
  if (planEmpty) histPlans.innerHTML = `<div class="muted">Not enough data yet.</div>`;

  state.weatherHistory.forEach((item) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.innerHTML = `
      <div class="icon">${conditionIcon(item.condition)}</div>
      <div class="history-meta">
        <div class="title">${item.city} • ${item.temp_c}°C</div>
        <div class="meta">${item.condition} • ${fmtRelative(item.created_at)}</div>
      </div>
    `;
    histWeather.append(div);
  });

  state.planHistory.forEach((item) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.innerHTML = `
      <div class="icon">📋</div>
      <div class="history-meta">
        <div class="title">${item.city}</div>
        <div class="meta">${item.condition} • [${(item.activities || []).join(", ")}] • ${fmtRelative(item.created_at)}</div>
      </div>
    `;
    histPlans.append(div);
  });
}

function buildForecast() {
  const baseTemp = state.currentWeather?.temp_c ?? 15;
  const now = new Date();
  const today = [];
  for (let i = 1; i <= 6; i++) {
    today.push({
      label: `${(now.getHours() + i) % 24}:00`,
      temp: (baseTemp + Math.sin(i / 2) * 2).toFixed(1),
      condition: state.currentWeather?.condition || "Cloudy",
    });
  }
  const days = [];
  for (let d = 1; d <= 5; d++) {
    const dayTemp = (baseTemp + Math.sin(d) * 3).toFixed(1);
    days.push({
      label: new Date(Date.now() + d * 86400000).toLocaleDateString(undefined, { weekday: "short" }),
      temp: dayTemp,
      condition: state.currentWeather?.condition || "Cloudy",
    });
  }
  state.forecast = { today, days };
}

function renderForecast() {
  const todayWrap = $("#forecast-today");
  const daysWrap = $("#forecast-days");
  todayWrap.innerHTML = "";
  daysWrap.innerHTML = "";
  state.forecast.today.forEach((f) => {
    const card = document.createElement("div");
    card.className = "forecast-card";
    card.innerHTML = `
      <div class="top"><span>${f.label}</span><span>${conditionIcon(f.condition)}</span></div>
      <div class="muted">${f.condition}</div>
      <div class="temp">${f.temp}°C</div>
    `;
    todayWrap.append(card);
  });
  state.forecast.days.forEach((f) => {
    const card = document.createElement("div");
    card.className = "forecast-card";
    card.innerHTML = `
      <div class="top"><span>${f.label}</span><span>${conditionIcon(f.condition)}</span></div>
      <div class="muted">${f.condition}</div>
      <div class="temp">${f.temp}°C</div>
    `;
    daysWrap.append(card);
  });
}

let chartUpdateTimeout = null;
function renderCharts() {
  if (chartUpdateTimeout) clearTimeout(chartUpdateTimeout);
  chartUpdateTimeout = setTimeout(() => {
    const temps = state.weatherHistory.slice().reverse();
    const labels = temps.map((w) => new Date(w.created_at).toLocaleTimeString());
    const dataPoints = temps.map((w) => w.temp_c);

    const tempCanvas = $("#temp-chart");
    const condCanvas = $("#condition-chart");

    const tempEmpty = dataPoints.length < 2;
    $("#temp-chart-empty").classList.toggle("hidden", !tempEmpty);
    tempCanvas.classList.toggle("hidden", tempEmpty);

    const condCounts = state.weatherHistory.reduce((acc, w) => {
      const key = (w.condition || "Unknown").toLowerCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
    const condLabels = Object.keys(condCounts);
    const condValues = Object.values(condCounts);
    const condEmpty = condValues.length < 1;
    $("#condition-chart-empty").classList.toggle("hidden", !condEmpty);
    condCanvas.classList.toggle("hidden", condEmpty);

    if (!tempEmpty) {
      if (state.charts.temp) state.charts.temp.destroy();
      state.charts.temp = new Chart(tempCanvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Temp °C",
              data: dataPoints,
              borderColor: "#3aa3ff",
              backgroundColor: "rgba(58,163,255,0.15)",
              fill: true,
              tension: 0.3,
            },
          ],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: "#9ba4b5" }, grid: { color: "rgba(255,255,255,0.05)" } },
            y: { ticks: { color: "#9ba4b5" }, grid: { color: "rgba(255,255,255,0.05)" } },
          },
        },
      });
    }

    if (!condEmpty) {
      if (state.charts.condition) state.charts.condition.destroy();
      state.charts.condition = new Chart(condCanvas, {
        type: "doughnut",
        data: {
          labels: condLabels,
          datasets: [
            {
              data: condValues,
              backgroundColor: ["#3aa3ff", "#6c5ce7", "#00c49a", "#ffb347", "#ff5c8a"],
            },
          ],
        },
        options: {
          plugins: { legend: { position: "bottom", labels: { color: "#f4f6fb" } } },
        },
      });
    }
  }, 300);
}

async function refreshAll() {
  await fetchHistory();
  renderHistoryLists();
  renderCharts();
}

async function handleGetWeather() {
  const city = $("#city").value.trim();
  if (!city) {
    showToast("Enter a city");
    return;
  }
  showLoader(true);
  try {
    await fetchWeather(city);
    renderWeatherCard();
    buildForecast();
    renderForecast();
    await refreshAll();
  } catch (e) {
    showToast(e.message || "API unavailable");
  } finally {
    showLoader(false);
  }
}

async function handleGetPlan() {
  const city = $("#city").value.trim();
  if (!city) {
    showToast("Enter a city");
    return;
  }
  showLoader(true);
  try {
    await fetchPlan(city);
    renderPlanCard();
    buildForecast();
    renderForecast();
    await refreshAll();
  } catch (e) {
    showToast(e.message || "API unavailable");
  } finally {
    showLoader(false);
  }
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      document.querySelectorAll("[data-tabpanel]").forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.tabpanel !== target);
      });
    });
  });

  const toggle = $("#history-toggle");
  toggle.addEventListener("click", () => {
    state.collapsedHistory = !state.collapsedHistory;
    const lists = document.querySelectorAll(".history-list");
    lists.forEach((el) => el.classList.toggle("hidden", state.collapsedHistory));
    toggle.textContent = state.collapsedHistory ? "Expand" : "Collapse";
  });
}

function setupShortcuts() {
  $("#city").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      handleGetWeather();
    }
  });
}

async function init() {
  lucide.createIcons();
  setupTabs();
  setupShortcuts();
  await fetchHealth();
  await refreshAll();
}

$("#btn-weather").addEventListener("click", handleGetWeather);
$("#btn-plan").addEventListener("click", handleGetPlan);

init().catch((e) => {
  console.error(e);
  showToast("Failed to init");
});
