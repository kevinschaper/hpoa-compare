"""Load HPOA-format annotation files into disease -> phenotype-term sets.

Both the Jax ``phenotype.hpoa`` and dismech's ``phenotype.dismech.hpoa`` share
the first 12 HPOA columns; dismech adds a 13th (``dismech_name``). We key the
Jax file by its native disease IDs (OMIM/ORPHA/DECIPHER) and the dismech file by
MONDO; the disease axis is reconciled later via MONDO SSSOM.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd


def load_hpoa(path: str | Path) -> pd.DataFrame:
    """Read an HPOA TSV, skipping ``#`` comment lines, using its header row."""
    df = pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        comment="#",
        keep_default_na=False,
    )
    df.columns = [c.strip().lstrip("#") for c in df.columns]
    return df


def disease_to_terms(
    df: pd.DataFrame,
    *,
    aspect: str | None = "P",
    positive_only: bool = True,
    hp_only: bool = True,
) -> dict[str, set[str]]:
    """Collapse rows to ``{disease_id: {hpo_id, ...}}``.

    aspect=None keeps all aspects; positive_only drops NOT-qualified rows;
    hp_only keeps only real ``HP:`` terms (drops dismech ``DISMECH:`` synthetics
    and any non-HP object).
    """
    out: dict[str, set[str]] = defaultdict(set)
    for row in df.itertuples(index=False):
        if aspect is not None and getattr(row, "aspect", "") != aspect:
            continue
        if positive_only and getattr(row, "qualifier", "") == "NOT":
            continue
        term = getattr(row, "hpo_id", "")
        if hp_only and not term.startswith("HP:"):
            continue
        out[row.database_id].add(term)
    return dict(out)


def disease_to_not_terms(df: pd.DataFrame) -> dict[str, set[str]]:
    """``{disease_id: {hpo_id}}`` for NOT-qualified (excluded) HP rows only."""
    out: dict[str, set[str]] = defaultdict(set)
    for row in df.itertuples(index=False):
        if getattr(row, "qualifier", "") != "NOT":
            continue
        term = getattr(row, "hpo_id", "")
        if term.startswith("HP:"):
            out[row.database_id].add(term)
    return dict(out)


def disease_labels(df: pd.DataFrame) -> dict[str, str]:
    return dict(zip(df["database_id"], df["disease_name"]))
