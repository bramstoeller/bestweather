"""Scoring logic: define what 'the best weather' means.

Best == as warm and dry as possible. We turn each day into a single score so
that forecasts from different providers can be compared and merged. The day with
the highest score wins.
"""

from typing import Dict, List

from .models import DayForecast

# Weights for the score. Tuned so that one degree warmer is roughly worth
# avoiding ~0.7mm of rain, and a fully-certain rain chance costs ~5 "degrees".
PRECIP_MM_PENALTY = 1.5
PRECIP_PROB_PENALTY = 0.05


def score(day: DayForecast) -> float:
    """Higher is better: warm boosts, precipitation and rain chance penalize."""
    value = day.temp_max
    value -= PRECIP_MM_PENALTY * (day.precip_mm or 0.0)
    if day.precip_prob is not None:
        value -= PRECIP_PROB_PENALTY * day.precip_prob
    return value


def merge_best(
    best: Dict[str, DayForecast], new_days: List[DayForecast], source: str
) -> bool:
    """Merge a provider's forecast into the running best-per-day map.

    Returns True when at least one day improved (so the frontend re-renders).
    """
    changed = False
    for day in new_days:
        day.source = source
        current = best.get(day.date)
        if current is None or score(day) > score(current):
            best[day.date] = day
            changed = True
    return changed
