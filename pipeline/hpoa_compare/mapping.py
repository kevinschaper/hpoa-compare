"""MONDO-centric disease-axis mapping via MONDO SSSOM.

MONDO is the canonical disease space. dismech is natively MONDO; HPOA is keyed by
OMIM/ORPHA/DECIPHER, so we lift HPOA *up* into MONDO via ``skos:exactMatch``.
Both sides then live in MONDO space, and dismech diseases that have no OMIM/ORPHA
counterpart are first-class coverage that extends beyond HPOA's rare-disease scope
-- not second-class "unmapped" entries.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# SSSOM object prefix -> HPOA database_id prefix.
HPOA_PREFIXES = {
    "OMIM": "OMIM",
    "Orphanet": "ORPHA",  # SSSOM writes Orphanet:, HPOA writes ORPHA:
    "DECIPHER": "DECIPHER",
}


def _to_hpoa_id(object_id: str) -> str | None:
    prefix, _, local = object_id.partition(":")
    hpoa_prefix = HPOA_PREFIXES.get(prefix)
    return f"{hpoa_prefix}:{local}" if hpoa_prefix else None


@dataclass
class DiseaseMap:
    mondo_to_hpoa: dict[str, set[str]]   # MONDO -> {OMIM/ORPHA/DECIPHER, ...}
    hpoa_to_mondo: dict[str, set[str]]   # OMIM/ORPHA/DECIPHER -> {MONDO, ...}
    mondo_labels: dict[str, str]

    def has_hpoa_xref(self, mondo: str) -> bool:
        """True if MONDO exact-matches any OMIM/ORPHA/DECIPHER disease at all."""
        return mondo in self.mondo_to_hpoa


def load_disease_map(
    sssom_path: str | Path,
    *,
    predicate: str = "skos:exactMatch",
) -> DiseaseMap:
    df = pd.read_csv(sssom_path, sep="\t", dtype=str, comment="#", keep_default_na=False)
    df = df[df["predicate_id"] == predicate]
    m2h: dict[str, set[str]] = defaultdict(set)
    h2m: dict[str, set[str]] = defaultdict(set)
    labels: dict[str, str] = {}
    has_label = "subject_label" in df.columns
    for r in df.itertuples(index=False):
        subj = r.subject_id
        if not subj.startswith("MONDO:"):
            continue
        hpoa_id = _to_hpoa_id(r.object_id)
        if not hpoa_id:
            continue
        m2h[subj].add(hpoa_id)
        h2m[hpoa_id].add(subj)
        if has_label and subj not in labels:
            labels[subj] = r.subject_label
    return DiseaseMap(dict(m2h), dict(h2m), labels)


def lift_hpoa_to_mondo(
    hpoa_terms: dict[str, set[str]],
    dmap: DiseaseMap,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Express HPOA annotations in MONDO space.

    Returns ``(mondo_terms, mondo_source_ids)`` where annotations from every
    OMIM/ORPHA/DECIPHER disease are unioned onto the MONDO term(s) they
    exact-match.
    """
    mondo_terms: dict[str, set[str]] = defaultdict(set)
    mondo_ids: dict[str, set[str]] = defaultdict(set)
    for hpoa_id, terms in hpoa_terms.items():
        for mondo in dmap.hpoa_to_mondo.get(hpoa_id, ()):
            mondo_terms[mondo] |= terms
            mondo_ids[mondo].add(hpoa_id)
    return dict(mondo_terms), dict(mondo_ids)
