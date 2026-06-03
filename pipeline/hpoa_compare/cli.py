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
    dmap = mapping.load_disease_map(INPUTS / "mondo.sssom.tsv")

    jax_terms = load.disease_to_terms(jax)
    dis_terms = load.disease_to_terms(dis)
    dis_labels = load.disease_labels(dis)

    # Lift HPOA up into MONDO space: both sides now keyed by MONDO.
    hpoa_mondo_terms, hpoa_mondo_ids = mapping.lift_hpoa_to_mondo(jax_terms, dmap)

    dismech_mondo = {m for m, t in dis_terms.items() if t}
    hpoa_mondo = {m for m, t in hpoa_mondo_terms.items() if t}
    both = dismech_mondo & hpoa_mondo
    dismech_only = dismech_mondo - hpoa_mondo   # dismech coverage beyond HPOA
    hpoa_only = hpoa_mondo - dismech_mondo       # HPOA diseases dismech lacks

    def _label(mondo: str) -> str:
        return dis_labels.get(mondo) or dmap.mondo_labels.get(mondo) or mondo

    click.echo("loading HPO closure (entailed_edge)...")
    hpo = HpoGraph(_hp_db())

    # --- per-disease phenotype comparison over shared MONDO diseases ---
    comparisons: list[metrics.DiseaseComparison] = []
    for mondo in sorted(both):
        comparisons.append(
            metrics.compare_disease(
                mondo,
                _label(mondo),
                sorted(hpoa_mondo_ids.get(mondo, set())),
                dis_terms[mondo],
                hpoa_mondo_terms[mondo],
                hpo,
            )
        )
    comparisons.sort(key=lambda c: c.closure.f1)

    # --- disease-axis coverage (MONDO-centric) ---
    dismech_only_rows = sorted(
        (
            {
                "mondo": m,
                "label": _label(m),
                "n_terms": len(dis_terms[m]),
                # has an OMIM/ORPHA xref HPOA *could* annotate, vs fully beyond
                "beyond_omim_orpha": not dmap.has_hpoa_xref(m),
            }
            for m in dismech_only
        ),
        key=lambda r: -r["n_terms"],
    )
    hpoa_only_rows = sorted(
        (
            {
                "mondo": m,
                "label": dmap.mondo_labels.get(m, m),
                "n_terms": len(hpoa_mondo_terms[m]),
                "hpoa_ids": sorted(hpoa_mondo_ids.get(m, set()))[:4],
            }
            for m in hpoa_only
        ),
        key=lambda r: -r["n_terms"],
    )
    disease_coverage = {
        "dismech_only": dismech_only_rows,
        "hpoa_only": hpoa_only_rows,
    }

    # --- term comparability (HP-typed vs DISMECH synthetic) ---
    dis_hp = int((dis["hpo_id"].str.startswith("HP:")).sum())
    dis_synth = int((dis["hpo_id"].str.startswith("DISMECH:")).sum())

    coverage = {
        "dismech_diseases": len(dismech_mondo),
        "hpoa_diseases_mondo": len(hpoa_mondo),
        "hpoa_diseases_raw": len(jax_terms),
        "comparable": len(both),
        "dismech_only": len(dismech_only),
        "dismech_only_beyond_omim_orpha": sum(r["beyond_omim_orpha"] for r in dismech_only_rows),
        "hpoa_only": len(hpoa_only),
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
    _write("disease_coverage.json", disease_coverage)

    click.echo(
        f"\nMONDO coverage: {len(both)} shared | "
        f"{len(dismech_only)} dismech-only "
        f"({coverage['dismech_only_beyond_omim_orpha']} beyond OMIM/ORPHA) | "
        f"{len(hpoa_only)} HPOA-only\n"
        f"closure micro-F1 {aggregates['closure']['micro']['f1']} "
        f"(exact {aggregates['exact']['micro']['f1']})"
    )


if __name__ == "__main__":
    cli()
