"""Offline lunar phase calculations using UTC internally."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

SYNODIC_MONTH_DAYS = 29.530588853
_J2000 = 2451545.0


@dataclass(frozen=True)
class MoonData:
    phase_name: str
    age_days: float
    illumination_percent: float
    waxing: bool
    next_phase_name: str
    next_phase_utc: datetime


_MAJOR_PHASES = (
    (0.0, "New Moon"),
    (0.25, "First Quarter"),
    (0.5, "Full Moon"),
    (0.75, "Last Quarter"),
)


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("A timezone-aware datetime is required.")
    return moment.astimezone(timezone.utc)


def _sin(degrees: float) -> float:
    return math.sin(math.radians(degrees))


def _cos(degrees: float) -> float:
    return math.cos(math.radians(degrees))


def _from_julian_day(julian_day: float) -> datetime:
    return datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=julian_day - _J2000)


def _delta_t_seconds(approximate_year: float) -> float:
    """Standard 2005--2050 approximation for converting TT to UTC."""
    year_offset = approximate_year - 2000
    return 62.92 + 0.32217 * year_offset + 0.005589 * year_offset**2


def _phase_event(k: float) -> datetime:
    """Return a major phase event in UTC, using Meeus chapter 49 periodic terms."""
    t = k / 1236.85
    t2, t3, t4 = t * t, t * t * t, t * t * t * t
    e = 1 - 0.002516 * t - 0.0000074 * t2
    m = 2.5534 + 29.10535670 * k - 0.0000014 * t2 - 0.00000011 * t3
    mp = 201.5643 + 385.81693528 * k + 0.0107582 * t2 + 0.00001238 * t3 - 0.000000058 * t4
    f = 160.7108 + 390.67050284 * k - 0.0016118 * t2 - 0.00000227 * t3 + 0.000000011 * t4
    omega = 124.7746 - 1.56375580 * k + 0.0020672 * t2 + 0.00000215 * t3
    phase = (k % 1 + 1) % 1
    shared = (
        0.01608 * _sin(2 * mp) + 0.01039 * _sin(2 * f)
        + 0.00739 * e * _sin(mp - m) - 0.00514 * e * _sin(mp + m)
        + 0.00208 * e**2 * _sin(2 * m) - 0.00111 * _sin(mp - 2 * f)
        - 0.00057 * _sin(mp + 2 * f) + 0.00056 * e * _sin(2 * mp + m)
        - 0.00042 * _sin(3 * mp) + 0.00042 * e * _sin(m + 2 * f)
        + 0.00038 * e * _sin(m - 2 * f) - 0.00024 * e * _sin(2 * mp - m)
        - 0.00017 * _sin(omega)
    )
    if math.isclose(phase, 0.0, abs_tol=1e-9):
        correction = shared - 0.40720 * _sin(mp) + 0.17241 * e * _sin(m)
    elif math.isclose(phase, 0.5, abs_tol=1e-9):
        correction = shared - 0.40614 * _sin(mp) + 0.17302 * e * _sin(m)
    else:
        correction = (
            -0.62801 * _sin(mp) + 0.17172 * e * _sin(m)
            - 0.01183 * e * _sin(mp + m) + 0.00862 * _sin(2 * mp)
            + 0.00804 * _sin(2 * f) + 0.00454 * e * _sin(mp - m)
            + 0.00204 * e**2 * _sin(2 * m) - 0.00180 * _sin(mp - 2 * f)
            - 0.00070 * _sin(mp + 2 * f) - 0.00040 * _sin(3 * mp)
            - 0.00034 * e * _sin(2 * mp - m) + 0.00032 * e * _sin(m + 2 * f)
            + 0.00032 * e * _sin(m - 2 * f) - 0.00028 * e**2 * _sin(mp + 2 * m)
            + 0.00027 * e * _sin(2 * mp + m) - 0.00017 * _sin(omega)
        )
        w = 0.00306 - 0.00038 * e * _cos(m) + 0.00026 * _cos(mp) - 0.00002 * _cos(mp - m) + 0.00002 * _cos(mp + m) + 0.00002 * _cos(2 * f)
        correction += w if phase < 0.5 else -w
    planetary = (
        0.000325 * _sin(299.77 + 0.107408 * k - 0.009173 * t2)
        + 0.000165 * _sin(251.88 + 0.016321 * k) + 0.000164 * _sin(251.83 + 26.651886 * k)
        + 0.000126 * _sin(349.42 + 36.412478 * k) + 0.000110 * _sin(84.66 + 18.206239 * k)
        + 0.000062 * _sin(141.74 + 53.303771 * k) + 0.000060 * _sin(207.14 + 2.453732 * k)
        + 0.000056 * _sin(154.84 + 7.306860 * k) + 0.000047 * _sin(34.52 + 27.261239 * k)
        + 0.000042 * _sin(207.19 + 0.121824 * k) + 0.000040 * _sin(291.34 + 1.844379 * k)
        + 0.000037 * _sin(161.72 + 24.198154 * k) + 0.000035 * _sin(239.56 + 25.513099 * k)
        + 0.000023 * _sin(331.55 + 3.592518 * k)
    )
    jde_tt = 2451550.09766 + 29.530588861 * k + 0.00015437 * t2 - 0.000000150 * t3 + 0.00000000073 * t4
    return _from_julian_day(jde_tt + correction + planetary - _delta_t_seconds(2000 + k / 12.3685) / 86_400)


def _nearby_events(moment: datetime) -> list[tuple[datetime, str]]:
    estimate = (moment.year + (moment.month - 0.5) / 12 - 2000) * 12.3685
    first_index = math.floor(estimate * 4) - 12
    return [(_phase_event(index / 4), _MAJOR_PHASES[index % 4][1]) for index in range(first_index, first_index + 32)]


def _phase_name(fraction: float) -> str:
    if fraction < 1 / 16 or fraction >= 15 / 16:
        return "New Moon"
    if fraction < 3 / 16:
        return "Waxing Crescent"
    if fraction < 5 / 16:
        return "First Quarter"
    if fraction < 7 / 16:
        return "Waxing Gibbous"
    if fraction < 9 / 16:
        return "Full Moon"
    if fraction < 11 / 16:
        return "Waning Gibbous"
    if fraction < 13 / 16:
        return "Last Quarter"
    return "Waning Crescent"


def calculate_moon_data(moment: datetime) -> MoonData:
    """Return Moon phase details for a timezone-aware datetime."""
    utc_moment = _utc(moment)
    events = _nearby_events(utc_moment)
    next_utc, next_name = next(event for event in events if event[0] > utc_moment)
    previous_new = max(time for time, name in events if name == "New Moon" and time <= utc_moment)
    following_new = min(time for time, name in events if name == "New Moon" and time > utc_moment)
    fraction = (utc_moment - previous_new).total_seconds() / (following_new - previous_new).total_seconds()
    age_days = (utc_moment - previous_new).total_seconds() / 86_400
    illumination = (1 - math.cos(2 * math.pi * fraction)) / 2
    return MoonData(
        phase_name=_phase_name(fraction),
        age_days=age_days,
        illumination_percent=illumination * 100,
        waxing=fraction < 0.5,
        next_phase_name=next_name,
        next_phase_utc=next_utc,
    )
