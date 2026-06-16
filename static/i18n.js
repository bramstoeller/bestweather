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
    meta_title: "BestWeather — the warmest & driest weather for your location",
    meta_description: "Compare every free weather API live and see the warmest, driest forecast for today and 14 days ahead. Search a place or use your location.",
    aria_lang: "Switch language",
    aria_theme: "Switch light/dark mode",
    aria_loc: "Use my location",
    about_title: "The warmest, driest weather — from every free source",
    about_text: "BestWeather queries several free weather services at once and shows the most optimistic forecast per day — as warm and dry as possible — for today and the next 14 days. The forecast updates live as each source comes in.",
    faq_title: "Frequently asked questions",
    faq_q1: "What does 'the best weather' mean?",
    faq_a1: "For each day we compute a score from temperature, precipitation and rain chance, then pick the warmest and driest forecast across every weather source.",
    faq_q2: "Which weather sources are used?",
    faq_a2: "Open-Meteo, MET Norway (yr.no) and Bright Sky (DWD), plus OpenWeatherMap and WeatherAPI.com when they are configured.",
    faq_q3: "Is BestWeather free?",
    faq_a3: "Yes. BestWeather uses only free, public weather APIs and needs no account. Your favorites stay private on your own device.",
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
    meta_title: "BestWeather — het warmste & droogste weer voor jouw locatie",
    meta_description: "Vergelijk live alle gratis weer-API's en zie per dag het warmste en droogste weer voor vandaag en 14 dagen vooruit. Zoek een plaats of gebruik je locatie.",
    aria_lang: "Wissel van taal",
    aria_theme: "Wissel licht/donker",
    aria_loc: "Gebruik mijn locatie",
    about_title: "Het warmste en droogste weer — uit elke gratis weerbron",
    about_text: "BestWeather bevraagt meerdere gratis weerdiensten tegelijk en toont per dag de meest optimistische voorspelling — zo warm en droog mogelijk — voor vandaag en de komende 14 dagen. De voorspelling werkt zich live bij terwijl de bronnen binnenkomen.",
    faq_title: "Veelgestelde vragen",
    faq_q1: "Wat betekent 'het beste weer'?",
    faq_a1: "Per dag berekenen we een score op basis van temperatuur, neerslag en regenkans, en kiezen we over alle weerbronnen de warmste en droogste voorspelling.",
    faq_q2: "Welke weerbronnen worden gebruikt?",
    faq_a2: "Open-Meteo, MET Norway (yr.no) en Bright Sky (DWD), aangevuld met OpenWeatherMap en WeatherAPI.com wanneer die zijn ingesteld.",
    faq_q3: "Is BestWeather gratis?",
    faq_a3: "Ja. BestWeather gebruikt uitsluitend gratis, openbare weer-API's en heeft geen account nodig. Je favorieten blijven privé op je eigen apparaat.",
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
