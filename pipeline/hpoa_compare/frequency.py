"""Flatten a frequency value to one of the six HP frequency bands.

Both resources encode frequency three ways in the HPOA column: an HP frequency
term (`HP:004028x`), a percentage (`75%`, `50-60%`), or an `n/m` ratio. We map
all of them to a band so the two sides can be compared on a common scale.

Band boundaries follow the HPO definitions:
  Obligate 100% · Very frequent 80-99% · Frequent 30-79% ·
  Occasional 5-29% · Very rare <5% (excl. 0) · Excluded 0%
"""
from __future__ import annotations

import re

# ordered most-frequent -> least-frequent, so adjacency = index distance
BANDS = [
    "HP:0040280",  # Obligate
    "HP:0040281",  # Very frequent
    "HP:0040282",  # Frequent
    "HP:0040283",  # Occasional
    "HP:0040284",  # Very rare
    "HP:0040285",  # Excluded
]
BAND_LABEL = {
    "HP:0040280": "Obligate",
    "HP:0040281": "Very frequent",
    "HP:0040282": "Frequent",
    "HP:0040283": "Occasional",
    "HP:0040284": "Very rare",
    "HP:0040285": "Excluded",
}
_INDEX = {b: i for i, b in enumerate(BANDS)}

_HP = re.compile(r"HP[:_](004028[0-5])$")
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_RATIO = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")


def _pct_to_band(p: float) -> str:
    if p <= 0:
        return "HP:0040285"
    if p < 5:
        return "HP:0040284"
    if p < 30:
        return "HP:0040283"
    if p < 80:
        return "HP:0040282"
    if p < 100:
        return "HP:0040281"
    return "HP:0040280"


def to_band(raw: str | None) -> str | None:
    """Normalize a raw frequency string to an HP frequency band, or None."""
    if not raw:
        return None
    s = str(raw).strip()
    m = _HP.match(s)
    if m:
        return f"HP:{m.group(1)}"
    m = _RANGE.search(s)
    if m:
        return _pct_to_band((float(m.group(1)) + float(m.group(2))) / 2)
    m = _PCT.search(s)
    if m:
        return _pct_to_band(float(m.group(1)))
    m = _RATIO.search(s)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        if den:
            return _pct_to_band(100 * num / den)
    return None


def distance(b1: str, b2: str) -> int:
    """Band-index distance (0 = same band, 1 = adjacent, ...)."""
    return abs(_INDEX[b1] - _INDEX[b2])
