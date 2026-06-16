"""How 'the best weather' is decided.

Every profile is an ideal point (target temperature, precipitation and wind)
plus a weight 0-3 for each of those three. A day scores by how close it sits to
the point, weighted. The point and weights encode as a short code
(`t25p0w5-231`) that doubles as the profile's URL segment, so built-ins,
tweaked built-ins and custom profiles all run through the same engine.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .models import DayForecast

Criterion = Callable[[DayForecast], float]

# Default ideal point + weights per built-in profile:
# (temp °C, precip mm, wind km/h, temp weight, precip weight, wind weight).
DEFAULTS: Dict[str, Tuple[float, float, float, int, int, int]] = {
    "general": (24, 0, 10, 2, 3, 1),
    "beach": (29, 0, 8, 3, 2, 1),
    "bbq": (24, 0, 8, 1, 3, 2),
    "outdoor": (16, 0, 16, 2, 2, 1),
    "windwater": (20, 0, 32, 1, 1, 3),
    "skating": (-6, 0, 8, 3, 2, 1),
    "skiing": (-3, 6, 12, 2, 3, 1),
}
DEFAULT = "general"
WEIGHTS_FALLBACK = (2, 3, 1)

SLUGS: Dict[str, str] = {
    "general": "algemeen",
    "beach": "strand",
    "bbq": "bbq",
    "outdoor": "buitensport",
    "windwater": "watersport",
    "skating": "schaatsen",
    "skiing": "skien",
}
_KEY_BY_SLUG = {slug: key for key, slug in SLUGS.items()}
_KEY_BY_SLUG.update({key: key for key in DEFAULTS})

_CUSTOM_RE = re.compile(
    r"^t(-?\d+(?:\.\d+)?)p(\d+(?:\.\d+)?)w(\d+(?:\.\d+)?)(?:-([0-4])([0-4])([0-4]))?$"
)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _near(getter, target: float, spread: float) -> Criterion:
    return lambda d: _clamp01(1.0 - abs((getter(d) or 0.0) - target) / spread)


@dataclass(frozen=True)
class Profile:
    key: str
    terms: Tuple[Tuple[float, Criterion], ...]

    def score(self, day: DayForecast) -> float:
        total = sum(w for w, _ in self.terms) or 1.0
        return 100.0 * sum(w * f(day) for w, f in self.terms) / total


def profile_from_values(temp, precip, wind, tw, pw, ww, key="custom") -> Profile:
    terms = []
    if tw:
        terms.append((tw, _near(lambda d: d.temp_max, float(temp), 12.0)))
    if pw:
        terms.append((pw, _near(lambda d: d.precip_mm, float(precip), 8.0)))
    if ww:
        terms.append((ww, _near(lambda d: d.wind_kmh, float(wind), 30.0)))
    if not terms:  # all weights zero -> fall back to temperature
        terms.append((1, _near(lambda d: d.temp_max, float(temp), 12.0)))
    return Profile(key, tuple(terms))


def parse_custom_code(code: str):
    """`t25p0w5-231` -> (temp, precip, wind, tw, pw, ww), or None."""
    m = _CUSTOM_RE.match(code or "")
    if not m:
        return None
    temp, precip, wind = float(m.group(1)), float(m.group(2)), float(m.group(3))
    if m.group(4) is not None:
        tw, pw, ww = int(m.group(4)), int(m.group(5)), int(m.group(6))
    else:
        tw, pw, ww = WEIGHTS_FALLBACK
    return temp, precip, wind, tw, pw, ww


def resolve_profile(activity: Optional[str]) -> Profile:
    """Map a URL activity segment (built-in slug or custom code) to a Profile."""
    key = _KEY_BY_SLUG.get(activity or SLUGS[DEFAULT])
    if key:
        return profile_from_values(*DEFAULTS[key], key=key)
    parsed = parse_custom_code(activity or "")
    if parsed:
        return profile_from_values(*parsed)
    return profile_from_values(*DEFAULTS[DEFAULT], key=DEFAULT)


def merge_best(best: Dict[str, DayForecast], new_days, source: str, profile: Profile) -> bool:
    """Merge a provider's days into the best-per-day map. True if anything improved."""
    changed = False
    for day in new_days:
        day.source = source
        day.score = profile.score(day)
        current = best.get(day.date)
        if current is None or day.score > (current.score if current.score is not None else -1.0):
            best[day.date] = day
            changed = True
    return changed
