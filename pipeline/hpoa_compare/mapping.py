"""MONDO SSSOM disease-axis mapping.

dismech is MONDO-anchored; Jax ``phenotype.hpoa`` uses OMIM/ORPHA/DECIPHER. We
resolve each MONDO disease to the *set* of HPOA disease IDs it ``skos:exactMatch``es
and later compare against the union of their HPOA annotations.
"""
from __future__ import annotations

from collections import defaultdict
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


def load_mondo_to_hpoa(
    sssom_path: str | Path,
    *,
    predicate: str = "skos:exactMatch",
) -> dict[str, set[str]]:
    """``{MONDO:id: {OMIM:..., ORPHA:..., ...}}`` for the given predicate."""
    df = pd.read_csv(sssom_path, sep="\t", dtype=str, comment="#", keep_default_na=False)
    df = df[df["predicate_id"] == predicate]
    out: dict[str, set[str]] = defaultdict(set)
    for subj, obj in zip(df["subject_id"], df["object_id"]):
        if not subj.startswith("MONDO:"):
            continue
        hpoa_id = _to_hpoa_id(obj)
        if hpoa_id:
            out[subj].add(hpoa_id)
    return dict(out)
