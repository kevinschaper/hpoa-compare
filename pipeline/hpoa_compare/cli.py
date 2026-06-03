"""Build the comparison artifacts consumed by the Observable Framework site."""
from __future__ import annotations

import json
from pathlib import Path

import click

from . import load, mapping, metrics
from .hpo import HpoGraph

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "data" / "inputs"
ARTIFACTS = ROOT / "src" / "data"

# fall back to OAK's local semsql cache if the pinned copy hasn't been fetched
_OAK_HP = Path.home() / ".data" / "oaklib" / "hp.db"


def _hp_db() -> Path:
    pinned = INPUTS / "hp.db"
    if pinned.exists():
        return pinned
    if _OAK_HP.exists():
        return _OAK_HP
    raise FileNotFoundError("hp.db not found; run `just fetch` or install via OAK")


def _write(name: str, obj) -> None:
    path = ARTIFACTS / name
    path.write_text(json.dumps(obj, indent=2))
    click.echo(f"  wrote {path.relative_to(ROOT)}")


@click.group()
def cli() -> None:
    """hpoa-compare pipeline."""


@cli.command()
def build() -> None:
    """Load inputs, map diseases, compute metrics, emit src/data/*.json."""
    click.echo("loading inputs...")
    jax = load.load_hpoa(INPUTS / "phenotype.hpoa")
    dis = load.load_hpoa(INPUTS / "phenotype.dismech.hpoa")
    m2h = mapping.load_mondo_to_hpoa(INPUTS / "mondo.sssom.tsv")

    jax_terms = load.disease_to_terms(jax)
    jax_labels = load.disease_labels(jax)
    dis_terms = load.disease_to_terms(dis)
    dis_labels = load.disease_labels(dis)

    click.echo("loading HPO closure (entailed_edge)...")
    hpo = HpoGraph(_hp_db())

    # --- per-disease comparison over dismech's MONDO diseases ---
    comparisons: list[metrics.DiseaseComparison] = []
    mappable = comparable = 0
    for mondo, d_terms in sorted(dis_terms.items()):
        hpoa_ids = m2h.get(mondo, set())
        if hpoa_ids:
            mappable += 1
        present = sorted(i for i in hpoa_ids if i in jax_terms)
        if not present or not d_terms:
            continue
        comparable += 1
        h_terms: set[str] = set().union(*(jax_terms[i] for i in present))
        comparisons.append(
            metrics.compare_disease(
                mondo, dis_labels.get(mondo, mondo), present, d_terms, h_terms, hpo
            )
        )

    comparisons.sort(key=lambda c: c.closure.f1)

    # --- term comparability (HP-typed vs DISMECH synthetic) ---
    dis_hp = int((dis["hpo_id"].str.startswith("HP:")).sum())
    dis_synth = int((dis["hpo_id"].str.startswith("DISMECH:")).sum())

    coverage = {
        "dismech_diseases": len(dis_terms),
        "mappable": mappable,
        "comparable": comparable,
        "hpoa_diseases": len(jax_terms),
        "dismech_rows_hp": dis_hp,
        "dismech_rows_synthetic": dis_synth,
        "term_comparability": round(dis_hp / (dis_hp + dis_synth), 4),
    }
    aggregates = {
        "n_comparable": len(comparisons),
        "exact": {
            "micro": metrics.micro_average(comparisons, "exact"),
            "macro": metrics.macro_average(comparisons, "exact"),
        },
        "closure": {
            "micro": metrics.micro_average(comparisons, "closure"),
            "macro": metrics.macro_average(comparisons, "closure"),
        },
        "total_novel": sum(c.n_novel for c in comparisons),
        "total_missing": sum(c.n_missing for c in comparisons),
        "more_specific": sum(c.more_specific for c in comparisons),
        "more_general": sum(c.more_general for c in comparisons),
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    click.echo("writing artifacts...")
    _write("coverage.json", coverage)
    _write("aggregates.json", aggregates)
    _write("per_disease.json", [c.to_row() for c in comparisons])

    click.echo(
        f"\ncomparable diseases: {len(comparisons)} | "
        f"closure micro-F1 {aggregates['closure']['micro']['f1']} "
        f"(exact {aggregates['exact']['micro']['f1']})"
    )


if __name__ == "__main__":
    cli()
