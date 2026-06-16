// MooisteWeer frontend: geolocation, search, favorites, weather profiles,
// per-place URLs, hourly detail, and the live websocket that streams the best
// forecast as each server-side source returns.

const PROFILE_ORDER = ["general", "beach", "bbq", "outdoor", "windwater", "skating", "skiing"];
const PROFILE_DEFAULTS = {
  general: { temp: 24, precip: 0, wind: 10 },
  beach: { temp: 29, precip: 0, wind: 8 },
  bbq: { temp: 24, precip: 0, wind: 8 },
  outdoor: { temp: 16, precip: 0, wind: 16 },
  windwater: { temp: 20, precip: 0, wind: 32 },
  skating: { temp: -6, precip: 0, wind: 8 },
  skiing: { temp: -3, precip: 6, wind: 12 },
};
const PROFILE_ICON = {
  general: "🌤️", beach: "🏖️", bbq: "🍖", outdoor: "🏃",
  windwater: "🏄", skating: "⛸️", skiing: "⛷️",
};
const PROFILE_SLUG = {
  general: "algemeen", beach: "strand", bbq: "bbq", outdoor: "buitensport",
  windwater: "watersport", skating: "schaatsen", skiing: "skien",
};
const SLUG_TO_KEY = {};
for (const k in PROFILE_SLUG) { SLUG_TO_KEY[PROFILE_SLUG[k]] = k; SLUG_TO_KEY[k] = k; }

const state = {
  lang: detectLang(),
  theme: localStorage.getItem("bw_theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  place: null,
  days: [],
  expanded: new Set(),
  changedDates: new Set(),
  profileKey: localStorage.getItem("mw_profile") || "general",
  scan: null,
  sources: [],
  ws: null,
  reqId: 0,
  notFound: null,
};

const $ = (id) => document.getElementById(id);

// ---------- Profiles ----------
function getOverrides() { try { return JSON.parse(localStorage.getItem("mw_overrides") || "{}"); } catch { return {}; } }
function setOverrides(o) { localStorage.setItem("mw_overrides", JSON.stringify(o)); }
function getCustoms() { try { return JSON.parse(localStorage.getItem("mw_customs") || "[]"); } catch { return []; } }
function setCustoms(list) { localStorage.setItem("mw_customs", JSON.stringify(list)); }

function num(x) { return Number.isInteger(x) ? x : Math.round(x * 10) / 10; }
function customCode(p) { return `t${num(p.temp)}p${num(p.precip)}w${num(p.wind)}`; }
function parseCode(code) {
  const m = /^t(-?\d+(?:\.\d+)?)p(\d+(?:\.\d+)?)w(\d+(?:\.\d+)?)$/.exec(code || "");
  return m ? { temp: +m[1], precip: +m[2], wind: +m[3] } : null;
}
function isCustomKey(pk) { return !PROFILE_DEFAULTS[pk] && !!parseCode(pk); }
function pointFor(pk) {
  if (PROFILE_DEFAULTS[pk]) return getOverrides()[pk] || PROFILE_DEFAULTS[pk];
  return parseCode(pk) || PROFILE_DEFAULTS.general;
}
function activityFor(pk) { return PROFILE_DEFAULTS[pk] ? PROFILE_SLUG[pk] : pk; }
function wsProfile(pk) { return customCode(pointFor(pk)); }
function profileIcon(pk) { return isCustomKey(pk) ? "✨" : (PROFILE_ICON[pk] || "✨"); }
function profileLabel(pk) {
  if (isCustomKey(pk)) {
    const c = getCustoms().find((c) => customCode(c) === pk);
    return c ? c.name : t(state.lang, "customize");
  }
  return t(state.lang, "profile_" + pk);
}
function profileDesc(pk) {
  const p = pointFor(pk);
  const wet = p.precip >= 1 ? `${p.precip} mm` : t(state.lang, "w_dry");
  const wind = p.wind <= 12 ? t(state.lang, "w_calm") : p.wind >= 25 ? t(state.lang, "w_windy") : t(state.lang, "w_moderate");
  return `${t(state.lang, "w_around")} ${p.temp}° · ${wet} · ${wind}`;
}
function profileKeyFromActivity(seg) {
  if (!seg) return null;
  if (SLUG_TO_KEY[seg]) return SLUG_TO_KEY[seg];
  return parseCode(seg) ? seg : null;
}

function profileRelevant(key) {
  // Hide clearly out-of-season profiles: no skating prompt at 30°C, no beach in
  // a frost. Uses today's forecast temperature when known, else the month.
  const temp = state.days.length ? state.days[0].temp_max : null;
  const m = new Date().getMonth();
  const warm = temp != null ? temp >= 16 : (m >= 3 && m <= 9);
  const cold = temp != null ? temp <= 9 : (m <= 2 || m >= 10);
  if (key === "skating" || key === "skiing") return cold;
  if (key === "beach") return warm;
  return true;
}

function renderProfiles() {
  const el = $("profiles");
  const builtins = PROFILE_ORDER.filter((k) => k === "general" || k === state.profileKey || profileRelevant(k));
  const keys = [...builtins, ...getCustoms().map(customCode)];
  let html = keys.map((pk) => {
    const active = pk === state.profileKey ? " active" : "";
    return `<button class="profile${active}" data-pk="${escapeAttr(pk)}" title="${escapeAttr(profileDesc(pk))}">` +
      `<span class="ico">${profileIcon(pk)}</span>${escapeHtml(profileLabel(pk))}</button>`;
  }).join("");
  html += `<button class="profile edit" id="editProfiles">✏️ ${t(state.lang, "customize")}</button>`;
  el.innerHTML = html;
  el.querySelectorAll("[data-pk]").forEach((b) =>
    b.addEventListener("click", () => selectProfile(b.dataset.pk)));
  $("editProfiles").addEventListener("click", openProfileModal);
}
function selectProfile(pk) {
  state.profileKey = pk;
  localStorage.setItem("mw_profile", pk);
  renderProfiles();
  if (state.place) { pushUrl(); subscribe(state.place); }
}

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
function brandHtml() {
  return state.lang === "nl" ? 'Mooiste<span class="accent">Weer</span>' : 'Best<span class="accent">Weather</span>';
}
function applyLang() {
  document.documentElement.lang = state.lang;
  document.title = t(state.lang, "meta_title");
  const md = document.querySelector('meta[name="description"]');
  if (md) md.setAttribute("content", t(state.lang, "meta_description"));
  document.querySelector(".brand h1").innerHTML = brandHtml();
  $("langBtn").textContent = state.lang === "nl" ? "EN" : "NL";
  $("langBtn").setAttribute("aria-label", t(state.lang, "aria_lang"));
  $("themeBtn").setAttribute("aria-label", t(state.lang, "aria_theme"));
  $("locBtn").setAttribute("aria-label", t(state.lang, "aria_loc"));
  $("searchInput").placeholder = t(state.lang, "search_placeholder");
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(state.lang, el.dataset.i18n); });
  renderProfiles();
  renderFavorites();
  renderPlaceName();
  if (state.notFound) renderNotFound();
  else if (state.days.length) renderForecast();
}
function toggleLang() {
  state.lang = state.lang === "nl" ? "en" : "nl";
  localStorage.setItem("bw_lang", state.lang);
  applyLang();
}

// ---------- Weather icon ----------
function emojiFor(code, precip, temp) {
  if (code != null) {
    if (code === 0) return "☀️";
    if (code <= 2) return "🌤️";
    if (code === 3) return "☁️";
    if (code === 45 || code === 48) return "🌫️";
    if (code >= 51 && code <= 67) return "🌧️";
    if (code >= 71 && code <= 77) return "❄️";
    if (code >= 80 && code <= 82) return "🌦️";
    if (code >= 85 && code <= 86) return "🌨️";
    if (code >= 95) return "⛈️";
  }
  const p = precip || 0;
  if (p >= 5) return "🌧️";
  if (p >= 1) return "🌦️";
  if (p >= 0.2) return "🌤️";
  return (temp ?? 0) >= 22 ? "☀️" : "🌤️";
}

// ---------- Favorites ----------
function getFavorites() { try { return JSON.parse(localStorage.getItem("bw_favorites") || "[]"); } catch { return []; } }
function saveFavorites(list) { localStorage.setItem("bw_favorites", JSON.stringify(list)); }
function favKey(p) { return `${p.lat.toFixed(3)},${p.lon.toFixed(3)}`; }
function isFavorite(p) { return p && getFavorites().some((f) => favKey(f) === favKey(p)); }
function toggleFavorite(p) {
  let list = getFavorites();
  if (list.some((f) => favKey(f) === favKey(p))) list = list.filter((f) => favKey(f) !== favKey(p));
  else list.push({ name: p.name, admin1: p.admin1, country: p.country, lat: p.lat, lon: p.lon });
  saveFavorites(list);
  renderFavorites();
  renderPlaceName();
}
function renderFavorites() {
  const el = $("favorites");
  const list = getFavorites();
  el.innerHTML = list.map((f, i) =>
    `<span class="chip" data-fav="${i}">📍 ${escapeHtml(f.name)} <span class="x" data-favx="${i}">✕</span></span>`
  ).join("");
  el.querySelectorAll("[data-fav]").forEach((c) => c.addEventListener("click", (e) => {
    if (e.target.dataset.favx != null) return;
    selectPlace(list[+c.dataset.fav]);
  }));
  el.querySelectorAll("[data-favx]").forEach((x) => x.addEventListener("click", (e) => {
    e.stopPropagation();
    saveFavorites(getFavorites().filter((_, i) => i !== +x.dataset.favx));
    renderFavorites(); renderPlaceName();
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
    renderResults((await r.json()).results);
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
    b.addEventListener("click", () => selectPlace(results[+b.dataset.r])));
}
function closeResults() { $("results").classList.remove("open"); }
document.addEventListener("click", (e) => { if (!e.target.closest(".search")) closeResults(); });

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
  }, (err) => setStatusText(t(state.lang, err.code === 1 ? "geo_denied" : "geo_unavailable")),
  { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
}

// ---------- URL routing ----------
function pushUrl() {
  if (!state.place) return;
  const segs = [state.place.country, state.place.admin1, state.place.name]
    .filter(Boolean).map(encodeURIComponent);
  // No profile chosen means "general", so we leave the activity off the URL.
  let url = "/" + segs.join("/");
  if (state.profileKey !== "general") url += "/" + activityFor(state.profileKey);
  if (location.pathname !== url) history.pushState({}, "", url);
}
function parseUrl() {
  const segs = location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  let activity = null;
  if (segs.length && profileKeyFromActivity(segs[segs.length - 1])) activity = segs.pop();
  return {
    city: segs[segs.length - 1] || null,
    admin1: segs[segs.length - 2] || null,
    country: segs[segs.length - 3] || null,
    activity,
  };
}
async function resolveFromPath(parsed) {
  if (parsed.activity) { const pk = profileKeyFromActivity(parsed.activity); if (pk) state.profileKey = pk; }
  const eq = (a, b) => (a || "").toLowerCase() === (b || "").toLowerCase();
  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(parsed.city)}&lang=${state.lang}`);
    const { results } = await r.json();
    if (!results || !results.length) return showNotFound(parsed.city);
    let pick = results[0];
    if (parsed.admin1 || parsed.country) {
      const m = results.find((x) =>
        (!parsed.admin1 || eq(x.admin1, parsed.admin1)) && (!parsed.country || eq(x.country, parsed.country)));
      if (m) pick = m;
    }
    selectPlace(pick, false);
  } catch { showNotFound(parsed.city); }
}
window.addEventListener("popstate", () => {
  const parsed = parseUrl();
  if (parsed.city) resolveFromPath(parsed);
});

// ---------- Place selection & websocket ----------
function selectPlace(place, push = true) {
  state.place = place;
  state.notFound = null;
  state.days = [];
  state.expanded = new Set();
  $("searchInput").value = "";
  closeResults();
  localStorage.setItem("bw_last", JSON.stringify(place));
  if (push) pushUrl();
  renderPlaceName();
  $("forecast").innerHTML = "";
  subscribe(place);
}
function showNotFound(q) {
  state.place = null;
  state.notFound = q;
  state.days = [];
  $("placeName").innerHTML = "";
  $("status").innerHTML = "";
  $("sourcesBox").hidden = true;
  renderNotFound();
}
function renderNotFound() {
  $("forecast").innerHTML = `<p class="notfound">${escapeHtml(t(state.lang, "not_found", { q: state.notFound }))}</p>`;
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
  state.scan = { done: 0, total: 0, sources: [], statuses: {} };
  renderStatus();
  try {
    const ws = await ensureSocket();
    if (myReq !== state.reqId) return;
    ws.send(JSON.stringify({ type: "subscribe", lat: place.lat, lon: place.lon, profile: wsProfile(state.profileKey) }));
  } catch { setStatusText(""); }
}
function onMessage(ev) {
  const msg = JSON.parse(ev.data);
  if (msg.type === "providers") {
    state.sources = msg.sources;
    state.scan = { done: 0, total: msg.total, sources: msg.sources, statuses: {} };
    renderStatus(); renderSources();
  } else if (msg.type === "update") {
    state.scan.done = msg.done; state.scan.total = msg.total;
    state.scan.statuses[msg.provider] = msg.status;
    if (msg.changed) updateDays(msg.days);
    renderStatus(); renderSources();
    if (msg.changed) renderForecast();
  } else if (msg.type === "complete") {
    state.scan.done = msg.total;
    updateDays(msg.days);
    renderStatus(true); renderSources(); renderForecast(); renderProfiles();
  }
}
function updateDays(days) {
  const prev = {};
  state.days.forEach((d) => { prev[d.date] = `${d.temp_max}|${d.precip_mm}|${d.source}`; });
  state.changedDates = new Set();
  days.forEach((d) => {
    const sig = `${d.temp_max}|${d.precip_mm}|${d.source}`;
    if (prev[d.date] !== undefined && prev[d.date] !== sig) state.changedDates.add(d.date);
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
    `<span>📍 ${escapeHtml(p.name)}${sub ? ` <span class="sub">· ${escapeHtml(sub)}</span>` : ""}</span>` +
    `<button class="icon-btn" id="favBtn" title="${escapeAttr(t(state.lang, fav ? "remove_favorite" : "save_favorite"))}" style="width:34px;height:34px;font-size:1rem">${fav ? "★" : "☆"}</button>`;
  $("favBtn").addEventListener("click", () => toggleFavorite(p));
}

function setStatusText(text) { $("status").innerHTML = text ? `<span>${escapeHtml(text)}</span>` : ""; }
function renderStatus(done = false) {
  const s = state.scan;
  if (!s || !s.total) return;
  const text = done ? t(state.lang, "all_done", { total: s.total }) : t(state.lang, "scanning", { done: s.done, total: s.total });
  $("status").innerHTML = `${done ? "" : '<span class="spinner"></span>'}<span>${escapeHtml(text)}</span>`;
}
function renderSources() {
  const sources = state.scan && state.scan.sources.length ? state.scan.sources : state.sources;
  if (!sources || !sources.length) { $("sourcesBox").hidden = true; return; }
  const statuses = (state.scan && state.scan.statuses) || {};
  $("sourcesBox").hidden = false;
  $("sourceList").innerHTML = sources.map((src) => {
    const st = statuses[src.name] || "";
    const tag = src.region && src.region !== "global" ? `<span class="tag">${src.region}</span>` : "";
    return `<a class="src-item" href="${escapeAttr(src.url)}" target="_blank" rel="noopener">` +
      `<span class="dot ${st}"></span>${escapeHtml(src.name)}${tag}</a>`;
  }).join("");
}

function fmtDow(date) { return I18N[state.lang].weekdays[new Date(date + "T00:00:00").getDay()]; }
function fmtDate(date) { const d = new Date(date + "T00:00:00"); return `${d.getDate()} ${I18N[state.lang].months[d.getMonth()]}`; }
function r0(n) { return Math.round(n); }
function precipText(d) {
  if ((d.precip_mm || 0) >= 0.2) return `${(d.precip_mm).toFixed(1)} mm`;
  if (d.precip_prob != null && d.precip_prob >= 30) return `${d.precip_prob}%`;
  return t(state.lang, "dry");
}
function windText(d) { return d.wind_kmh != null ? `${r0(d.wind_kmh)} km/h` : ""; }
function metaLine(d) { return [precipText(d), windText(d)].filter(Boolean).join(" · "); }

function hoursHtml(d, isToday) {
  if (!d.hourly || !d.hourly.length) return "";
  const nowH = new Date().getHours();
  const cells = d.hourly.filter((h) => !isToday || parseInt(h.time) >= nowH).map((h) =>
    `<div class="hour"><div>${h.time}</div><div class="h-emoji">${emojiFor(h.code, h.precip, h.temp)}</div>` +
    `<div class="h-temp">${r0(h.temp)}°</div><div>${r0(h.wind)}</div></div>`
  ).join("");
  return `<div class="hours">${cells}</div>`;
}

function renderForecast() {
  if (!state.days.length) return;
  const [today, ...rest] = state.days;

  const todayHtml = `
    <div class="today-card" data-day="${today.date}">
      <div class="today-top">
        <div>
          <div class="today-label">${escapeHtml(t(state.lang, "today"))}</div>
          <div class="today-temp">${r0(today.temp_max)}°<small>${today.temp_min != null ? " / " + r0(today.temp_min) + "°" : ""}</small></div>
          <div class="today-meta">${escapeHtml(metaLine(today))}</div>
        </div>
        <div class="today-emoji">${emojiFor(today.weather_code, today.precip_mm, today.temp_max)}</div>
      </div>
      <div class="today-source">${escapeHtml(t(state.lang, "source"))}: ${escapeHtml(today.source || "-")}</div>
      ${state.expanded.has(today.date) ? hoursHtml(today, true) : ""}
    </div>`;

  const daysHtml = rest.map((d) => {
    const changed = state.changedDates.has(d.date) ? " changed" : "";
    return `
      <div class="day${changed}" data-day="${d.date}">
        <div><div class="dow">${fmtDow(d.date)}</div><div class="date">${fmtDate(d.date)}</div></div>
        <div class="emoji">${emojiFor(d.weather_code, d.precip_mm, d.temp_max)}</div>
        <div class="meta">${escapeHtml(metaLine(d))}</div>
        <div class="temps"><span class="tmax">${r0(d.temp_max)}°</span>${d.temp_min != null ? `<span class="tmin">${r0(d.temp_min)}°</span>` : ""}</div>
      </div>
      ${state.expanded.has(d.date) ? `<div class="grid-hours">${hoursHtml(d, false)}</div>` : ""}`;
  }).join("");

  $("forecast").innerHTML = todayHtml + `<div class="grid">${daysHtml}</div>`;
  $("forecast").querySelectorAll("[data-day]").forEach((el) =>
    el.addEventListener("click", () => toggleDay(el.dataset.day)));
}
function toggleDay(date) {
  if (state.expanded.has(date)) state.expanded.delete(date); else state.expanded.add(date);
  renderForecast();
}

// ---------- Profile modal ----------
function openProfileModal() {
  const o = getOverrides();
  const builtins = PROFILE_ORDER.map((k) => {
    const p = o[k] || PROFILE_DEFAULTS[k];
    return `<div class="prow" data-builtin="${k}">
      <div class="pname">${PROFILE_ICON[k]} ${escapeHtml(t(state.lang, "profile_" + k))}</div>
      <button class="linkbtn" data-reset="${k}">${escapeHtml(t(state.lang, "reset_default"))}</button>
      ${fieldsHtml(p)}
    </div>`;
  }).join("");
  const customs = getCustoms().map((c, i) =>
    `<div class="prow" data-custom="${i}">
      <div class="pname"><input class="name-input" data-f="name" value="${escapeAttr(c.name)}" placeholder="${escapeAttr(t(state.lang, "field_name"))}"></div>
      <button class="linkbtn" data-del="${i}">${escapeHtml(t(state.lang, "delete"))}</button>
      ${fieldsHtml(c)}
    </div>`).join("");

  $("profileModal").innerHTML = `
    <div class="modal-card">
      <div class="modal-head">
        <h2>${escapeHtml(t(state.lang, "customize"))}</h2>
        <button class="icon-btn" id="modalClose">✕</button>
      </div>
      <h3>${escapeHtml(t(state.lang, "edit_builtin_title"))}</h3>
      ${builtins}
      <h3>${escapeHtml(t(state.lang, "custom_title"))}</h3>
      <div id="customRows">${customs}</div>
      <button class="btn" id="addCustom">＋ ${escapeHtml(t(state.lang, "add_custom"))}</button>
      <div class="modal-actions">
        <button class="btn" id="modalCancel">${escapeHtml(t(state.lang, "close"))}</button>
        <button class="btn primary" id="modalSave">${escapeHtml(t(state.lang, "save"))}</button>
      </div>
    </div>`;
  $("profileModal").hidden = false;

  $("modalClose").addEventListener("click", closeModal);
  $("modalCancel").addEventListener("click", closeModal);
  $("profileModal").addEventListener("click", (e) => { if (e.target.id === "profileModal") closeModal(); });
  $("modalSave").addEventListener("click", saveProfiles);
  $("addCustom").addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "prow"; row.dataset.custom = "new";
    row.innerHTML = `<div class="pname"><input class="name-input" data-f="name" placeholder="${escapeAttr(t(state.lang, "field_name"))}"></div>
      <button class="linkbtn" data-delnew="1">${escapeHtml(t(state.lang, "delete"))}</button>
      ${fieldsHtml({ temp: 22, precip: 0, wind: 10 })}`;
    $("customRows").appendChild(row);
    row.querySelector("[data-delnew]").addEventListener("click", () => row.remove());
  });
  $("profileModal").querySelectorAll("[data-reset]").forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.reset, def = PROFILE_DEFAULTS[k], row = b.closest(".prow");
    row.querySelector('[data-f="temp"]').value = def.temp;
    row.querySelector('[data-f="precip"]').value = def.precip;
    row.querySelector('[data-f="wind"]').value = def.wind;
  }));
  $("profileModal").querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => b.closest(".prow").remove()));
}
function fieldsHtml(p) {
  const f = (key, label, val) => `<label class="field">${escapeHtml(t(state.lang, label))}<input type="number" data-f="${key}" value="${val}"></label>`;
  return `<div class="fields">${f("temp", "field_temp", p.temp)}${f("precip", "field_precip", p.precip)}${f("wind", "field_wind", p.wind)}</div>`;
}
function readPoint(row) {
  const v = (k) => parseFloat(row.querySelector(`[data-f="${k}"]`).value);
  return { temp: v("temp"), precip: v("precip"), wind: v("wind") };
}
function saveProfiles() {
  const overrides = {};
  $("profileModal").querySelectorAll("[data-builtin]").forEach((row) => {
    const k = row.dataset.builtin, p = readPoint(row), def = PROFILE_DEFAULTS[k];
    if (p.temp !== def.temp || p.precip !== def.precip || p.wind !== def.wind) overrides[k] = p;
  });
  setOverrides(overrides);
  const customs = [];
  $("profileModal").querySelectorAll("[data-custom]").forEach((row) => {
    const name = (row.querySelector('[data-f="name"]').value || "").trim();
    if (!name) return;
    customs.push({ name, ...readPoint(row) });
  });
  setCustoms(customs);
  closeModal();
  renderProfiles();
  if (state.place) subscribe(state.place);
}
function closeModal() { $("profileModal").hidden = true; $("profileModal").innerHTML = ""; }

// ---------- Helpers ----------
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ---------- Boot ----------
$("themeBtn").addEventListener("click", toggleTheme);
$("langBtn").addEventListener("click", toggleLang);
applyTheme();
applyLang();

// Always show the source links (attribution), even before a forecast loads.
fetch("/api/health").then((r) => r.json()).then((d) => {
  state.sources = d.sources || [];
  renderSources();
}).catch(() => {});

(function boot() {
  const parsed = parseUrl();
  if (parsed.city) { resolveFromPath(parsed); return; }
  if (parsed.activity) { const pk = profileKeyFromActivity(parsed.activity); if (pk) { state.profileKey = pk; renderProfiles(); } }
  const last = localStorage.getItem("bw_last");
  if (last) { try { selectPlace(JSON.parse(last)); return; } catch {} }
  if (navigator.geolocation) useMyLocation();
})();
