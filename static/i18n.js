// Translations. Code/keys in English; Dutch translation provided.
// Brand name "BestWeather" is intentionally not translated.
const I18N = {
  en: {
    tagline: "The warmest & driest forecast, from every free weather API.",
    search_placeholder: "Search a city or place…",
    use_my_location: "Use my location",
    favorites: "Favorites",
    no_favorites: "No favorites yet — save a place with the ★.",
    save_favorite: "Save as favorite",
    remove_favorite: "Remove favorite",
    today: "Today",
    scanning: "Scanning {done}/{total} weather sources…",
    all_done: "Done — best of {total} weather sources.",
    locating: "Finding your location…",
    geo_denied: "Location access denied. Search for a place instead.",
    geo_unavailable: "Location unavailable. Search for a place instead.",
    pick_location: "Search a place or use your location to begin.",
    high: "High",
    low: "Low",
    rain: "Rain",
    rain_chance: "chance",
    source: "Best source",
    error_sources: "Some sources failed.",
    lang_name: "EN",
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    months: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
  },
  nl: {
    tagline: "Het warmste & droogste weer, uit elke gratis weer-API.",
    search_placeholder: "Zoek een stad of plaats…",
    use_my_location: "Gebruik mijn locatie",
    favorites: "Favorieten",
    no_favorites: "Nog geen favorieten — bewaar een plaats met de ★.",
    save_favorite: "Bewaar als favoriet",
    remove_favorite: "Verwijder favoriet",
    today: "Vandaag",
    scanning: "Bezig met {done}/{total} weerbronnen…",
    all_done: "Klaar — beste van {total} weerbronnen.",
    locating: "Je locatie wordt bepaald…",
    geo_denied: "Geen toegang tot locatie. Zoek anders een plaats.",
    geo_unavailable: "Locatie niet beschikbaar. Zoek anders een plaats.",
    pick_location: "Zoek een plaats of gebruik je locatie om te starten.",
    high: "Max",
    low: "Min",
    rain: "Regen",
    rain_chance: "kans",
    source: "Beste bron",
    error_sources: "Sommige bronnen faalden.",
    lang_name: "NL",
    weekdays: ["zo", "ma", "di", "wo", "do", "vr", "za"],
    months: ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"],
  },
};

function detectLang() {
  const saved = localStorage.getItem("bw_lang");
  if (saved && I18N[saved]) return saved;
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return I18N[nav] ? nav : "en";
}

function t(lang, key, vars) {
  let s = (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
  if (vars) for (const k in vars) s = s.replace(`{${k}}`, vars[k]);
  return s;
}
