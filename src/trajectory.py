"""
ROIC trajectory for the research result.

The fitted curve is ROIC(t) = ROIC_terminal + (ROIC_0 - ROIC_terminal) * e^(-λt),
with t = 0 in the first reported year. "Today" is the latest year on file.
Year 5 and year 10 are measured from that year, so the chart and the
takeaways use the same percents.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


def project_roic(t: float, roic_0: float, lam: float, terminal: float) -> float:
    """Exponential decay (or recovery) toward the terminal return."""
    return terminal + (roic_0 - terminal) * math.exp(-lam * t)


def percent_label(value: float) -> str:
    """Nearest whole percent, half rounding away from zero via floor(x+0.5)."""
    rounded = int(math.floor(value * 100 + 0.5))
    return f"{rounded}%"


def _versus_long_run(roic: float, terminal: float) -> str:
    gap = roic - terminal
    long_run = percent_label(terminal)
    if gap >= 0.08:
        return f"still well above the long-run {long_run}"
    if gap >= 0.03:
        return f"still above the long-run {long_run}"
    if gap > 0.02:
        return f"only a little above the long-run {long_run}"
    if gap >= -0.02:
        return f"close to the long-run {long_run}"
    if gap > -0.08:
        return f"a little below the long-run {long_run}"
    return f"below the long-run {long_run}"


def _pace(current: float, future: float, terminal: float) -> str:
    """
    How the advantage moves over the horizon.

    Returns one of: holding, fading slowly, fading, near.
    """
    gap_now = current - terminal
    gap_future = future - terminal
    if abs(gap_future) <= 0.02 or abs(gap_now) <= 0.015:
        return "near"
    if gap_future * gap_now < 0:
        return "near"
    retained = gap_future / gap_now
    closed = 1 - retained
    if closed < 0.15:
        return "holding"
    if closed < 0.50:
        return "fading slowly"
    return "fading"


def _pace_sentence(pace: str) -> str:
    if pace == "near":
        return "The advantage is already near the terminal level."
    if pace == "holding":
        return "The advantage is holding."
    if pace == "fading slowly":
        return "The advantage is fading slowly."
    return "The advantage is fading."


def _ten_year_meaning(current: float, y10: float, terminal: float) -> str:
    """
    One plain-English reading of the 10-year level.

    wide: the return stays high and a real premium is still there.
    commodity: the return has fallen to a low, undifferentiated level.
    narrow: the premium is mostly gone and the level is only moderate.
    """
    # Whole percents at or under 12% read as undifferentiated returns.
    if int(math.floor(y10 * 100 + 0.5)) <= 12 or terminal <= 0.10:
        return "commodity"
    gap_10 = y10 - terminal
    gap_now = current - terminal
    retained = (gap_10 / gap_now) if gap_now > 0.005 else 1.0
    if y10 >= 0.25 or (y10 >= 0.20 and gap_10 >= 0.03 and retained >= 0.30):
        return "wide"
    return "narrow"


def _meaning_clause(pace: str, meaning: str) -> str:
    if meaning == "commodity":
        if pace == "near":
            return "The advantage is already near the terminal level, so returns fall toward a commodity level."
        if pace == "holding":
            return "The advantage is holding, though returns sit near a commodity level."
        if pace == "fading slowly":
            return "The advantage is fading slowly, and returns fall toward a commodity level."
        return "The advantage is fading, and returns fall toward a commodity level."
    if meaning == "wide":
        if pace == "near":
            return "The advantage is already near the terminal level, and it is a wide moat that lasts."
        if pace == "holding":
            return "The advantage is holding, and it is a wide moat that lasts."
        if pace == "fading slowly":
            return "The advantage is fading slowly, but it is a wide moat that lasts."
        return "The advantage is fading, but it is a wide moat that lasts."
    if pace == "near":
        return "The advantage is already near the terminal level, and it is a narrow moat that erodes."
    if pace == "holding":
        return "The advantage is holding, though it is a narrow moat that erodes."
    if pace == "fading slowly":
        return "The advantage is fading slowly, and it is a narrow moat that erodes."
    return "The advantage is fading, and it is a narrow moat that erodes."


def five_year_takeaway(current: float, y5: float, terminal: float) -> str:
    pace = _pace(current, y5, terminal)
    return (
        f"In 5 years, return on capital is about {percent_label(y5)}, "
        f"{_versus_long_run(y5, terminal)}. {_pace_sentence(pace)}"
    )


def ten_year_takeaway(current: float, y10: float, terminal: float) -> str:
    pace = _pace(current, y10, terminal)
    meaning = _ten_year_meaning(current, y10, terminal)
    return (
        f"In 10 years, return on capital is about {percent_label(y10)}, "
        f"{_versus_long_run(y10, terminal)}. {_meaning_clause(pace, meaning)}"
    )


def _clean_history(history: Sequence[Any]) -> List[Tuple[int, float]]:
    points: List[Tuple[int, float]] = []
    for item in history:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        year, roic = item[0], item[1]
        if year is None or roic is None:
            continue
        try:
            year_i = int(year)
            roic_f = float(roic)
        except (TypeError, ValueError):
            continue
        points.append((year_i, roic_f))
    points.sort(key=lambda pair: pair[0])
    return points


def build_trajectory(fundamentals: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Historical points plus a 10-year projection.

    Returns None when the company has no fitted decay or no yearly history,
    so the UI can hide the chart instead of inventing a series.
    """
    if not fundamentals:
        return None

    decay = fundamentals.get("decay_params") or {}
    lam = decay.get("lambda")
    roic_0 = decay.get("roic_0")
    terminal = decay.get("roic_terminal")
    if lam is None or roic_0 is None or terminal is None:
        return None

    try:
        lam_f = float(lam)
        roic_0_f = float(roic_0)
        terminal_f = float(terminal)
    except (TypeError, ValueError):
        return None

    history = _clean_history(fundamentals.get("roic_history") or [])
    if not history:
        return None

    origin = history[0][0]
    latest = history[-1][0]

    def at_year(year: float) -> float:
        return project_roic(year - origin, roic_0_f, lam_f, terminal_f)

    current = at_year(latest)
    y5 = at_year(latest + 5)
    y10 = at_year(latest + 10)

    # Quarterly steps keep the drawn curve smooth without changing year 5 or 10.
    forecast = []
    step = 0
    while True:
        year = latest + step * 0.25
        if year > latest + 10 + 1e-9:
            break
        forecast.append({"year": round(year, 2), "roic": round(at_year(year), 4)})
        step += 1

    return {
        "as_of_year": latest,
        "historical": [
            {"year": year, "roic": round(roic, 4)}
            for year, roic in history
        ],
        "forecast": forecast,
        "terminal_roic": round(terminal_f, 4),
        "current_roic": round(current, 4),
        "year_5": {"year": latest + 5, "roic": round(y5, 4)},
        "year_10": {"year": latest + 10, "roic": round(y10, 4)},
        "takeaways": {
            "five_year": five_year_takeaway(current, y5, terminal_f),
            "ten_year": ten_year_takeaway(current, y10, terminal_f),
        },
    }
