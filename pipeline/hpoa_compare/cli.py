"""Build the comparison artifacts consumed by the Observable Framework site."""
from __future__ import annotations

import json
from pathlib import Path

import click

from . import load, mapping, metrics
from .hpo import HpoGraph
from .mondo import MondoGraph

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

    replaced_by = mapping.load_replaced_by(ROOT / "data" / "mondo_replaced_by.tsv")

    jax_terms = load.disease_to_terms(jax)
    dis_terms_raw = load.disease_to_terms(dis)
    dis_labels = load.disease_labels(dis)

    # Resolve obsolete MONDO terms on the dismech side too, so both sides agree.
    dis_terms: dict[str, set[str]] = {}
    for m, t in dis_terms_raw.items():
        dis_terms.setdefault(mapping.resolve_obsolete(m, replaced_by), set()).update(t)

    # Lift HPOA up into MONDO space (obsolete targets redirected to live terms).
    hpoa_mondo_terms, hpoa_mondo_ids = mapping.lift_hpoa_to_mondo(jax_terms, dmap, replaced_by)

    # Exclude the ontology root and other non-disease groupings that would sweep
    # in the entire subtree as "covered".
    NON_DISEASE = {"MONDO:0000001"}  # "disease" (root)
    dismech_mondo = {m for m, t in dis_terms.items() if t and m not in NON_DISEASE}
    hpoa_mondo = {m for m, t in hpoa_mondo_terms.items() if t}
    exact_shared = dismech_mondo & hpoa_mondo

    def _label(mondo: str) -> str:
        return dis_labels.get(mondo) or dmap.mondo_labels.get(mondo) or mondo

    click.echo("loading MONDO is-a graph (release KGX)...")
    mg = MondoGraph(INPUTS / "mondo_edges.tsv", INPUTS / "mondo_nodes.tsv")
    click.echo("loading HPO closure (entailed_edge)...")
    hpo = HpoGraph(_hp_db())

    # --- lineage-aware disease matching (disease-axis analogue of phenotype closure) ---
    # A dismech grouping disease covers HPOA annotations on its subtype (descendant)
    # MONDO nodes; a dismech subtype is covered by an HPOA grouping (ancestor).
    # Bounded to LINEAGE_HOPS so matching means "adjacent granularity / same disease",
    # not "anywhere in the category" (which would let a grouping swallow its subtree).
    LINEAGE_HOPS = 2
    comparisons: list[metrics.DiseaseComparison] = []
    dismech_only: list[str] = []
    covered_hpoa: set[str] = set()   # HPOA MONDO nodes on some dismech disease's lineage
    for d in sorted(dismech_mondo):
        if d in hpoa_mondo:
            match_type, h_match = "exact", {d}
        else:
            anc = (mg.ancestors_within(d, LINEAGE_HOPS) - {d}) & hpoa_mondo
            desc = (mg.descendants_within(d, LINEAGE_HOPS) - {d}) & hpoa_mondo
            h_match = anc | desc
            if not h_match:
                dismech_only.append(d)
                continue
            match_type = "mixed" if (anc and desc) else "descendant" if desc else "ancestor"
        covered_hpoa |= h_match
        h_terms: set[str] = set().union(*(hpoa_mondo_terms[h] for h in h_match))
        h_ids = sorted(set().union(*(hpoa_mondo_ids[h] for h in h_match)))
        comparisons.append(
            metrics.compare_disease(
                d, _label(d), h_ids, dis_terms[d], h_terms, hpo,
                match_type=match_type, n_hpoa_nodes=len(h_match),
            )
        )
    comparisons.sort(key=lambda c: c.closure.f1)
    exact_comps = [c for c in comparisons if c.match_type == "exact"]
    lineage_comps = [c for c in comparisons if c.match_type != "exact"]

    hpoa_only = hpoa_mondo - covered_hpoa
    hpoa_lineage_covered = covered_hpoa - exact_shared

    # --- disease-axis coverage rows ---
    dismech_only_rows = sorted(
        ({"mondo": m, "label": _label(m), "n_terms": len(dis_terms[m]),
          "beyond_omim_orpha": not dmap.has_hpoa_xref(m)} for m in dismech_only),
        key=lambda r: -r["n_terms"],
    )
    lineage_rows = sorted(
        ({"mondo": c.mondo, "label": c.label, "match_type": c.match_type,
          "n_hpoa_nodes": c.n_hpoa_nodes, "closure_f1": c.closure.f1} for c in lineage_comps),
        key=lambda r: -r["n_hpoa_nodes"],
    )
    hpoa_only_rows = sorted(
        ({"mondo": m, "label": dmap.mondo_labels.get(m, m),
          "n_terms": len(hpoa_mondo_terms[m]),
          "hpoa_ids": sorted(hpoa_mondo_ids.get(m, set()))[:4]} for m in hpoa_only),
        key=lambda r: -r["n_terms"],
    )
    disease_coverage = {
        "dismech_only": dismech_only_rows,
        "lineage_shared": lineage_rows,
        "hpoa_only": hpoa_only_rows,
    }

    # --- term comparability (HP-typed vs DISMECH synthetic) ---
    dis_hp = int((dis["hpo_id"].str.startswith("HP:")).sum())
    dis_synth = int((dis["hpo_id"].str.startswith("DISMECH:")).sum())

    coverage = {
        "dismech_diseases": len(dismech_mondo),
        "hpoa_diseases_mondo": len(hpoa_mondo),
        "hpoa_diseases_raw": len(jax_terms),
        "exact_shared": len(exact_shared),
        "lineage_shared": len(lineage_comps),
        "dismech_only": len(dismech_only),
        "dismech_only_beyond_omim_orpha": sum(r["beyond_omim_orpha"] for r in dismech_only_rows),
        "hpoa_lineage_covered": len(hpoa_lineage_covered),
        "hpoa_only": len(hpoa_only),
        "dismech_rows_hp": dis_hp,
        "dismech_rows_synthetic": dis_synth,
        "term_comparability": round(dis_hp / (dis_hp + dis_synth), 4),
    }
    # Phenotype aggregates are over EXACT MONDO matches only: lineage (grouping)
    # matches union subtype annotations and would distort recall.
    aggregates = {
        "n_scored_exact": len(exact_comps),
        "n_lineage": len(lineage_comps),
        "scored_set": "exact MONDO matches",
        "exact": {
            "micro": metrics.micro_average(exact_comps, "exact"),
            "macro": metrics.macro_average(exact_comps, "exact"),
        },
        "closure": {
            "micro": metrics.micro_average(exact_comps, "closure"),
            "macro": metrics.macro_average(exact_comps, "closure"),
        },
        "total_novel": sum(c.n_novel for c in exact_comps),
        "total_missing": sum(c.n_missing for c in exact_comps),
        "more_specific": sum(c.more_specific for c in exact_comps),
        "more_general": sum(c.more_general for c in exact_comps),
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    click.echo("writing artifacts...")
    _write("coverage.json", coverage)
    _write("aggregates.json", aggregates)
    _write("per_disease.json", [c.to_row() for c in comparisons])
    _write("disease_coverage.json", disease_coverage)

    click.echo(
        f"\nMONDO coverage: {len(exact_shared)} exact-shared + {len(lineage_comps)} "
        f"lineage-shared | {len(dismech_only)} dismech-only | {len(hpoa_only)} HPOA-only\n"
        f"phenotype (exact matches): closure micro-F1 "
        f"{aggregates['closure']['micro']['f1']} (exact {aggregates['exact']['micro']['f1']})"
    )


if __name__ == "__main__":
    cli()
