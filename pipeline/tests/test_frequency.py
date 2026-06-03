"""Tests for frequency -> HP band normalization."""
from hpoa_compare import frequency as freq


def test_hp_terms_pass_through():
    assert freq.to_band("HP:0040282") == "HP:0040282"
    assert freq.to_band("HP_0040281") == "HP:0040281"


def test_percent_to_band():
    assert freq.to_band("100%") == "HP:0040280"   # Obligate
    assert freq.to_band("90%") == "HP:0040281"    # Very frequent
    assert freq.to_band("50%") == "HP:0040282"    # Frequent
    assert freq.to_band("20%") == "HP:0040283"    # Occasional
    assert freq.to_band("2%") == "HP:0040284"     # Very rare
    assert freq.to_band("0%") == "HP:0040285"     # Excluded


def test_range_uses_midpoint():
    assert freq.to_band("50-60%") == "HP:0040282"   # mid 55 -> Frequent
    assert freq.to_band("80-99%") == "HP:0040281"   # mid ~90 -> Very frequent


def test_ratio_to_band():
    assert freq.to_band("1/1") == "HP:0040280"      # 100% -> Obligate
    assert freq.to_band("1/2") == "HP:0040282"      # 50% -> Frequent
    assert freq.to_band("1/4") == "HP:0040283"      # 25% -> Occasional
    assert freq.to_band("1/100") == "HP:0040284"    # 1% -> Very rare


def test_missing_and_unparseable():
    assert freq.to_band("") is None
    assert freq.to_band(None) is None
    assert freq.to_band("often") is None


def test_distance():
    assert freq.distance("HP:0040282", "HP:0040282") == 0
    assert freq.distance("HP:0040282", "HP:0040283") == 1   # adjacent
    assert freq.distance("HP:0040281", "HP:0040285") == 4   # very frequent vs excluded
