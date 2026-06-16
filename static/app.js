// BestWeather frontend: geolocation, search, favorites, and the live websocket
// that streams progressively-better forecasts as each server-side source returns.

const state = {
  lang: detectLang(),
  theme: localStorage.getItem("bw_theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  place: null,        // {name, admin1, country, lat, lon}
  days: [],           // latest best-per-day forecast
  prevKeys: new Set(),// dates whose values changed, for the pop animation
  ws: null,
  reqId: 0,           // guards against stale websocket responses
};

const $ = (id) => document.getElementById(id);

// ---------- Theme & language ----------
function applyTheme() {
  document.documentElement.setAttribute("data-theme", state.theme);
  $("themeBtn").textContent = state.theme === "dark" ? "☀️" : "🌙";
}
function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem("bw_theme", state.theme);
  applyTheme();
}
function applyLang() {
  document.documentElement.lang = state.lang;
  $("langBtn").textContent = state.lang === "nl" ? "EN" : "NL";
  $("searchInput").placeholder = t(state.lang, "search_placeholder");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(state.lang, el.dataset.i18n);
  });
  renderFavorites();
  if (state.days.length) renderForecast();
  else renderStatus();
}
function toggleLang() {
  state.lang = state.lang === "nl" ? "en" : "nl";
  localStorage.setItem("bw_lang", state.lang);
  applyLang();
}

// ---------- Weather icon ----------
function emojiFor(day) {
  const c = day.weather_code;
  if (c != null) {
    if (c === 0) return "☀️";
    if (c <= 2) return "🌤️";
    if (c === 3) return "☁️";
    if (c === 45 || c === 48) return "🌫️";
    if (c >= 51 && c <= 67) return "🌧️";
    if (c >= 71 && c <= 77) return "❄️";
    if (c >= 80 && c <= 82) return "🌦️";
    if (c >= 85 && c <= 86) return "🌨️";
    if (c >= 95) return "⛈️";
  }
  // Fallback when a source gives no weather code: infer from precip & temp.
  const p = day.precip_mm || 0;
  if (p >= 5) return "🌧️";
  if (p >= 1) return "🌦️";
  if (p >= 0.2) return "🌤️";
  return (day.temp_max ?? 0) >= 22 ? "☀️" : "🌤️";
}

// ---------- Favorites (localStorage) ----------
function getFavorites() {
  try { return JSON.parse(localStorage.getItem("bw_favorites") || "[]"); }
  catch { return []; }
}
function saveFavorites(list) {
  localStorage.setItem("bw_favorites", JSON.stringify(list));
}
function favKey(p) { return `${p.lat.toFixed(3)},${p.lon.toFixed(3)}`; }
function isFavorite(p) {
  return p && getFavorites().some((f) => favKey(f) === favKey(p));
}
function toggleFavorite(p) {
  let list = getFavorites();
  if (list.some((f) => favKey(f) === favKey(p))) {
    list = list.filter((f) => favKey(f) !== favKey(p));
  } else {
    list.push({ name: p.name, admin1: p.admin1, country: p.country, lat: p.lat, lon: p.lon });
  }
  saveFavorites(list);
  renderFavorites();
  renderPlaceName();
}
function renderFavorites() {
  const el = $("favorites");
  const list = getFavorites();
  let html = `<div class="fav-label">${t(state.lang, "favorites")}</div>`;
  if (!list.length) {
    html += `<span class="chip empty">${t(state.lang, "no_favorites")}</span>`;
  } else {
    html += list.map((f, i) =>
      `<span class="chip" data-fav="${i}">📍 ${escapeHtml(f.name)} <span class="x" data-favx="${i}">✕</span></span>`
    ).join("");
  }
  el.innerHTML = html;
  el.querySelectorAll("[data-fav]").forEach((c) => c.addEventListener("click", (e) => {
    if (e.target.dataset.favx != null) return;
    selectPlace(list[+c.dataset.fav]);
  }));
  el.querySelectorAll("[data-favx]").forEach((x) => x.addEventListener("click", (e) => {
    e.stopPropagation();
    const next = getFavorites().filter((_, i) => i !== +x.dataset.favx);
    saveFavorites(next); renderFavorites(); renderPlaceName();
  }));
}

// ---------- Search ----------
let searchTimer = null;
$("searchInput").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  if (q.length < 2) { closeResults(); return; }
  searchTimer = setTimeout(() => doSearch(q), 250);
});
async function doSearch(q) {
  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&lang=${state.lang}`);
    const { results } = await r.json();
    renderResults(results);
  } catch { closeResults(); }
}
function renderResults(results) {
  const el = $("results");
  if (!results || !results.length) { closeResults(); return; }
  el.innerHTML = results.map((r, i) => {
    const sub = [r.admin1, r.country].filter(Boolean).join(", ");
    return `<button data-r="${i}">${escapeHtml(r.name)} <span class="muted">${escapeHtml(sub)}</span></button>`;
  }).join("");
  el.classList.add("open");
  el.querySelectorAll("[data-r]").forEach((b) =>
    b.addEventListener("click", () => { selectPlace(results[+b.dataset.r]); }));
}
function closeResults() { $("results").classList.remove("open"); }
document.addEventListener("click", (e) => {
  if (!e.target.closest(".search")) closeResults();
});

// ---------- Geolocation ----------
$("locBtn").addEventListener("click", useMyLocation);
function useMyLocation() {
  if (!navigator.geolocation) { setStatusText(t(state.lang, "geo_unavailable")); return; }
  setStatusText(t(state.lang, "locating"));
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const { latitude: lat, longitude: lon } = pos.coords;
    let place = { name: t(state.lang, "today"), lat, lon };
    try {
      const r = await fetch(`/api/reverse?lat=${lat}&lon=${lon}&lang=${state.lang}`);
      const data = await r.json();
      if (data.place) place = data.place;
    } catch {}
    selectPlace(place);
  }, (err) => {
    setStatusText(t(state.lang, err.code === 1 ? "geo_denied" : "geo_unavailable"));
  }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
}

// ---------- Place selection & websocket ----------
function selectPlace(place) {
  state.place = place;
  $("searchInput").value = "";
  closeResults();
  state.days = [];
  state.prevKeys = new Set();
  localStorage.setItem("bw_last", JSON.stringify(place));
  renderPlaceName();
  $("forecast").innerHTML = "";
  subscribe(place);
}

function ensureSocket() {
  return new Promise((resolve, reject) => {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) return resolve(state.ws);
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    state.ws = ws;
    ws.addEventListener("message", onMessage);
    ws.addEventListener("open", () => resolve(ws));
    ws.addEventListener("error", reject);
    ws.addEventListener("close", () => { if (state.ws === ws) state.ws = null; });
  });
}
async function subscribe(place) {
  const myReq = ++state.reqId;
  state.scan = { done: 0, total: 0, providers: [], statuses: {} };
  renderStatus();
  try {
    const ws = await ensureSocket();
    if (myReq !== state.reqId) return;
    ws.send(JSON.stringify({ type: "subscribe", lat: place.lat, lon: place.lon }));
  } catch {
    setStatusText(t(state.lang, "error_sources"));
  }
}
function onMessage(ev) {
  const msg = JSON.parse(ev.data);
  if (msg.type === "providers") {
    state.scan = { done: 0, total: msg.total, providers: msg.providers, statuses: {} };
    renderStatus();
  } else if (msg.type === "update") {
    state.scan.done = msg.done;
    state.scan.total = msg.total;
    state.scan.statuses[msg.provider] = msg.status;
    if (msg.changed) updateDays(msg.days);
    renderStatus();
    if (msg.changed) renderForecast();
  } else if (msg.type === "complete") {
    state.scan.done = msg.total;
    updateDays(msg.days);
    renderStatus(true);
    renderForecast();
  }
}
function updateDays(days) {
  // Track which days changed so we can animate them.
  const prev = {};
  state.days.forEach((d) => { prev[d.date] = `${d.temp_max}|${d.precip_mm}|${d.source}`; });
  state.prevKeys = new Set();
  days.forEach((d) => {
    const sig = `${d.temp_max}|${d.precip_mm}|${d.source}`;
    if (prev[d.date] !== undefined && prev[d.date] !== sig) state.prevKeys.add(d.date);
  });
  state.days = days;
}

// ---------- Rendering ----------
function renderPlaceName() {
  const el = $("placeName");
  if (!state.place) { el.innerHTML = ""; return; }
  const p = state.place;
  const sub = [p.admin1, p.country].filter(Boolean).join(", ");
  const fav = isFavorite(p);
  el.innerHTML =
    `<span>📍 ${escapeHtml(p.name)}${sub ? ` <span style="color:var(--muted);font-weight:400">· ${escapeHtml(sub)}</span>` : ""}</span>` +
    `<button class="icon-btn" id="favBtn" title="${t(state.lang, fav ? "remove_favorite" : "save_favorite")}" style="width:34px;height:34px;font-size:1rem">${fav ? "★" : "☆"}</button>`;
  $("favBtn").addEventListener("click", () => toggleFavorite(p));
}

function setStatusText(text) { $("status").innerHTML = `<span>${escapeHtml(text)}</span>`; }
function renderStatus(done = false) {
  const s = state.scan;
  if (!s || !s.total) {
    if (!state.place) setStatusText("");
    return;
  }
  const dots = s.providers.map((name) => {
    const st = s.statuses[name] || "";
    return `<span class="dot ${st}" title="${escapeHtml(name)}: ${st || "…"}"></span>`;
  }).join("");
  const text = done
    ? t(state.lang, "all_done", { total: s.total })
    : t(state.lang, "scanning", { done: s.done, total: s.total });
  const spinner = done ? "" : `<span class="spinner"></span>`;
  $("status").innerHTML = `${spinner}<span>${text}</span><span class="dots">${dots}</span>`;
}

function fmtDow(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return I18N[state.lang].weekdays[d.getDay()];
}
function fmtDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return `${d.getDate()} ${I18N[state.lang].months[d.getMonth()]}`;
}
function round(n) { return Math.round(n); }

function renderForecast() {
  if (!state.days.length) { $("forecast").innerHTML = ""; return; }
  const [today, ...rest] = state.days;

  const todayHtml = `
    <div class="today-card">
      <div class="today-top">
        <div>
          <div class="today-label">${t(state.lang, "today")}</div>
          <div class="today-temp">${round(today.temp_max)}°<small>${today.temp_min != null ? " / " + round(today.temp_min) + "°" : ""}</small></div>
        </div>
        <div class="today-emoji">${emojiFor(today)}</div>
      </div>
      <div class="today-meta">
        <span>💧 ${t(state.lang, "rain")}: ${(today.precip_mm || 0).toFixed(1)} mm${today.precip_prob != null ? ` · ${today.precip_prob}% ${t(state.lang, "rain_chance")}` : ""}</span>
      </div>
      <div class="today-source">${t(state.lang, "source")}: ${escapeHtml(today.source || "—")}</div>
    </div>`;

  const daysHtml = rest.map((d) => {
    const changed = state.prevKeys.has(d.date) ? " changed" : "";
    return `
      <div class="day${changed}">
        <div><div class="dow">${fmtDow(d.date)}</div><div class="date">${fmtDate(d.date)}</div></div>
        <div class="emoji">${emojiFor(d)}</div>
        <div>
          <div class="rain">💧 ${(d.precip_mm || 0).toFixed(1)} mm${d.precip_prob != null ? ` · ${d.precip_prob}%` : ""}</div>
          <div class="src">${escapeHtml(d.source || "")}</div>
        </div>
        <div class="temps"><span class="tmax">${round(d.temp_max)}°</span>${d.temp_min != null ? `<span class="tmin">${round(d.temp_min)}°</span>` : ""}</div>
      </div>`;
  }).join("");

  $("forecast").innerHTML = todayHtml + `<div class="grid">${daysHtml}</div>`;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Boot ----------
$("themeBtn").addEventListener("click", toggleTheme);
$("langBtn").addEventListener("click", toggleLang);
applyTheme();
applyLang();
renderFavorites();

// Restore the last viewed place, otherwise try geolocation automatically.
(function boot() {
  const last = localStorage.getItem("bw_last");
  if (last) {
    try { selectPlace(JSON.parse(last)); return; } catch {}
  }
  if (navigator.geolocation) useMyLocation();
})();
