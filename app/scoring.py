"""How 'the best weather' is decided.

Every profile, built-in or custom, is one ideal point: a target temperature,
target precipitation and target wind. A day scores by how close it sits to that
point. The ideal point encodes as a short code (`t25p0w5`) that doubles as the
profile's URL segment, so built-ins, user-tweaked built-ins and fully custom
profiles all run through the same engine.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .models import DayForecast

Criterion = Callable[[DayForecast], float]

# Relative importance of (temperature, precipitation, wind) in the score.
WEIGHTS = (2.0, 1.5, 1.0)

# Default ideal point per built-in profile: (temp °C, precip mm, wind km/h).
DEFAULTS: Dict[str, Tuple[float, float, float]] = {
    "general": (24, 0, 10),
    "beach": (29, 0, 8),
    "bbq": (24, 0, 8),
    "outdoor": (16, 0, 16),
    "windwater": (20, 0, 32),
    "skating": (-6, 0, 8),
    "skiing": (-3, 6, 12),
}
DEFAULT = "general"

# URL slugs for built-in profiles (Dutch, used as the activity URL segment).
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

_CUSTOM_RE = re.compile(r"^t(-?\d+(?:\.\d+)?)p(\d+(?:\.\d+)?)w(\d+(?:\.\d+)?)$")


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


def profile_from_point(temp: float, precip: float, wind: float, key: str = "custom") -> Profile:
    return Profile(
        key,
        (
            (WEIGHTS[0], _near(lambda d: d.temp_max, temp, 12.0)),
            (WEIGHTS[1], _near(lambda d: d.precip_mm, precip, 8.0)),
            (WEIGHTS[2], _near(lambda d: d.wind_kmh, wind, 30.0)),
        ),
    )


def parse_custom_code(code: str) -> Optional[Tuple[float, float, float]]:
    """`t25p0w5` -> (25, 0, 5), or None."""
    m = _CUSTOM_RE.match(code or "")
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def custom_code(temp: float, precip: float, wind: float) -> str:
    n = lambda x: int(x) if float(x).is_integer() else x
    return f"t{n(temp)}p{n(precip)}w{n(wind)}"


def resolve_profile(activity: Optional[str]) -> Profile:
    """Map a URL activity segment (built-in slug or custom code) to a Profile."""
    key = _KEY_BY_SLUG.get(activity or SLUGS[DEFAULT])
    if key:
        return profile_from_point(*DEFAULTS[key], key=key)
    point = parse_custom_code(activity or "")
    if point:
        return profile_from_point(*point)
    return profile_from_point(*DEFAULTS[DEFAULT], key=DEFAULT)


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
