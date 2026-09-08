"""One dismech-vs-HPOA comparison, parameterized on the two annotation files.

``build`` (the current pair) and ``history`` (one pair per dismech release) both
run through :func:`compare_files`; the expensive, release-independent context
(MONDO map + graph, HPO graph) is loaded once and shared.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import frequency as freq
from . import load, mapping, metrics
from .hpo import HpoGraph
from .mondo import MondoGraph

# Ontology root and other non-disease groupings that would sweep in the entire
# subtree as "covered".
NON_DISEASE = {"MONDO:0000001"}  # "disease" (root)

# Disease-axis lineage matching is bounded so matching means "adjacent
# granularity / same disease", not "anywhere in the category".
LINEAGE_HOPS = 2


@dataclass
class Context:
    dmap: mapping.DiseaseMap
    replaced_by: dict[str, str]
    mondo: MondoGraph
    hpo: HpoGraph
    key: str  # fingerprint of the fixed inputs, for cache invalidation


def load_context(inputs: Path, replaced_by_path: Path) -> Context:
    dmap = mapping.load_disease_map(inputs / "mondo.sssom.tsv")
    replaced_by = mapping.load_replaced_by(replaced_by_path)
    mg = MondoGraph(inputs / "mondo_edges.tsv", inputs / "mondo_nodes.tsv")
    hpo = HpoGraph(inputs / "hp.obo")
    h = hashlib.sha256()
    for p in (inputs / "mondo.sssom.tsv", inputs / "mondo_edges.tsv", replaced_by_path):
        h.update(p.read_bytes())
    h.update(hpo.version.encode())
    return Context(dmap, replaced_by, mg, hpo, key=f"hp={hpo.version};fixed={h.hexdigest()[:12]}")


@dataclass
class Result:
    dismech_header: dict[str, str]
    hpoa_header: dict[str, str]
    comparisons: list[metrics.DiseaseComparison]        # exact + lineage matches
    dismech_only_comps: list[metrics.DiseaseComparison]  # no HPOA counterpart
    coverage: dict
    aggregates: dict
    frequency_summary: dict
    disease_coverage: dict = field(default_factory=dict)
    frequency_disagreements: list[dict] = field(default_factory=list)

    @property
    def exact(self) -> list[metrics.DiseaseComparison]:
        return [c for c in self.comparisons if c.match_type == "exact"]

    @property
    def browser(self) -> list[metrics.DiseaseComparison]:
        """Every dismech disease, matched or not, sorted by MONDO id."""
        return sorted(self.comparisons + self.dismech_only_comps, key=lambda c: c.mondo)


def compare_files(ctx: Context, dismech_path: Path, hpoa_path: Path, *,
                  keep_diffs: bool = True) -> Result:
    """Compare one dismech export against one ``phenotype.hpoa``.

    ``keep_diffs=False`` skips the per-disease term lists and the coverage /
    disagreement row tables (only scalars are needed for release history).
    """
    dmap, replaced_by, mg, hpo = ctx.dmap, ctx.replaced_by, ctx.mondo, ctx.hpo
    jax = load.load_hpoa(hpoa_path)
    dis = load.load_hpoa(dismech_path)

    jax_terms = load.disease_to_terms(jax)
    dis_terms_raw = load.disease_to_terms(dis)
    dis_labels = load.disease_labels(dis)

    # Resolve obsolete MONDO terms on the dismech side too, so both sides agree.
    dis_terms: dict[str, set[str]] = {}
    for m, t in dis_terms_raw.items():
        dis_terms.setdefault(mapping.resolve_obsolete(m, replaced_by), set()).update(t)

    # Lift HPOA up into MONDO space (obsolete targets redirected to live terms).
    hpoa_mondo_terms, hpoa_mondo_ids = mapping.lift_hpoa_to_mondo(jax_terms, dmap, replaced_by)

    # Frequency bands per (MONDO disease, phenotype), flattened to HP bands so the
    # two sides can be compared. dismech: direct; HPOA: mode across the OMIM/ORPHA
    # ids that lift to a MONDO (obsolete resolved).
    dismech_bands: dict[str, dict[str, str]] = defaultdict(dict)
    for (m, hp), raw in load.disease_phenotype_frequency(dis).items():
        band = freq.to_band(raw)
        if band:
            dismech_bands[mapping.resolve_obsolete(m, replaced_by)][hp] = band
    votes: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for (hid, hp), raw in load.disease_phenotype_frequency(jax).items():
        band = freq.to_band(raw)
        if not band:
            continue
        for m in dmap.hpoa_to_mondo.get(hid, ()):
            votes[mapping.resolve_obsolete(m, replaced_by)][hp][band] += 1
    hpoa_bands: dict[str, dict[str, str]] = {
        m: {hp: v.most_common(1)[0][0] for hp, v in hps.items()} for m, hps in votes.items()
    }

    dismech_mondo = {m for m, t in dis_terms.items() if t and m not in NON_DISEASE}
    hpoa_mondo = {m for m, t in hpoa_mondo_terms.items() if t}
    exact_shared = dismech_mondo & hpoa_mondo

    def _label(mondo: str) -> str:
        return dis_labels.get(mondo) or dmap.mondo_labels.get(mondo) or mondo

    # --- lineage-aware disease matching (disease-axis analogue of phenotype closure) ---
    # A dismech grouping disease covers HPOA annotations on its subtype (descendant)
    # MONDO nodes; a dismech subtype is covered by an HPOA grouping (ancestor).
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
        # frequency bands are meaningful only for exact matches, where the HPOA
        # node is the MONDO itself (lineage aggregates subtype frequencies).
        comparisons.append(
            metrics.compare_disease(
                d, _label(d), h_ids, dis_terms[d], h_terms, hpo,
                match_type=match_type, n_hpoa_nodes=len(h_match),
                dismech_bands=dismech_bands.get(d) if match_type == "exact" else None,
                hpoa_bands=hpoa_bands.get(d) if match_type == "exact" else None,
                keep_diffs=keep_diffs,
            )
        )
    comparisons.sort(key=lambda c: (c.closure.f1, c.mondo))
    exact_comps = [c for c in comparisons if c.match_type == "exact"]
    lineage_comps = [c for c in comparisons if c.match_type != "exact"]

    hpoa_only = hpoa_mondo - covered_hpoa
    hpoa_lineage_covered = covered_hpoa - exact_shared

    dismech_only_comps = [
        metrics.compare_disease(
            d, _label(d), [], dis_terms[d], set(), hpo,
            match_type="dismech-only", n_hpoa_nodes=0, keep_diffs=keep_diffs,
        )
        for d in sorted(dismech_only)
    ]

    # --- term comparability (HP-typed vs DISMECH synthetic) ---
    dis_hp = int((dis["hpo_id"].str.startswith("HP:")).sum())
    dis_synth = int((dis["hpo_id"].str.startswith("DISMECH:")).sum())
    n_dismech_only_beyond = sum(not dmap.has_hpoa_xref(m) for m in dismech_only)

    coverage = {
        "dismech_diseases": len(dismech_mondo),
        "hpoa_diseases_mondo": len(hpoa_mondo),
        "hpoa_diseases_raw": len(jax_terms),
        "exact_shared": len(exact_shared),
        "lineage_shared": len(lineage_comps),
        "dismech_only": len(dismech_only),
        "dismech_only_beyond_omim_orpha": n_dismech_only_beyond,
        "hpoa_lineage_covered": len(hpoa_lineage_covered),
        "hpoa_only": len(hpoa_only),
        "dismech_rows_hp": dis_hp,
        "dismech_rows_synthetic": dis_synth,
        "term_comparability": round(dis_hp / (dis_hp + dis_synth), 4) if (dis_hp + dis_synth) else 0.0,
        "hpoa_rows": int(len(jax)),
        "dismech_phenotype_pairs": sum(len(t) for t in dis_terms.values()),
        "hpoa_phenotype_pairs_mondo": sum(len(t) for t in hpoa_mondo_terms.values()),
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

    # --- frequency concordance on shared phenotypes (exact disease matches) ---
    # Computed from the band maps directly so it does not depend on keep_diffs.
    fc: Counter = Counter()
    disagreements: list[dict] = []
    for c in exact_comps:
        db_all, hb_all = dismech_bands.get(c.mondo, {}), hpoa_bands.get(c.mondo, {})
        for t in dis_terms[c.mondo] & hpoa_mondo_terms[c.mondo]:
            db, hb = db_all.get(t), hb_all.get(t)
            if db and hb:
                dist = freq.distance(db, hb)
                fc["same" if dist == 0 else "adjacent" if dist == 1 else "disagree"] += 1
                if dist >= 1 and keep_diffs:
                    disagreements.append({
                        "mondo": c.mondo, "disease": c.label,
                        "phenotype": t, "label": hpo.label(t),
                        "dismech": freq.BAND_LABEL[db], "hpoa": freq.BAND_LABEL[hb],
                        "distance": dist,
                    })
            elif db or hb:
                fc["one_side"] += 1
            else:
                fc["neither"] += 1
    disagreements.sort(key=lambda r: (-r["distance"], r["mondo"], r["phenotype"]))
    frequency_summary = {
        "same": fc["same"], "adjacent": fc["adjacent"], "disagree": fc["disagree"],
        "one_side_only": fc["one_side"], "neither_specified": fc["neither"],
        "both_specified": fc["same"] + fc["adjacent"] + fc["disagree"],
    }

    disease_coverage: dict = {}
    if keep_diffs:
        # secondary sort on mondo so ties are deterministic (set iteration is not)
        disease_coverage = {
            "dismech_only": sorted(
                ({"mondo": m, "label": _label(m), "n_terms": len(dis_terms[m]),
                  "beyond_omim_orpha": not dmap.has_hpoa_xref(m)} for m in dismech_only),
                key=lambda r: (-r["n_terms"], r["mondo"]),
            ),
            "lineage_shared": sorted(
                ({"mondo": c.mondo, "label": c.label, "match_type": c.match_type,
                  "n_hpoa_nodes": c.n_hpoa_nodes, "closure_f1": c.closure.f1}
                 for c in lineage_comps),
                key=lambda r: (-r["n_hpoa_nodes"], r["mondo"]),
            ),
            "hpoa_only": sorted(
                ({"mondo": m, "label": dmap.mondo_labels.get(m, m),
                  "n_terms": len(hpoa_mondo_terms[m]),
                  "hpoa_ids": sorted(hpoa_mondo_ids.get(m, set()))[:4]} for m in hpoa_only),
                key=lambda r: (-r["n_terms"], r["mondo"]),
            ),
        }

    return Result(
        dismech_header=load.read_header(dismech_path),
        hpoa_header=load.read_header(hpoa_path),
        comparisons=comparisons,
        dismech_only_comps=dismech_only_comps,
        coverage=coverage,
        aggregates=aggregates,
        frequency_summary=frequency_summary,
        disease_coverage=disease_coverage,
        frequency_disagreements=disagreements,
    )


def history_rows(c: metrics.DiseaseComparison) -> dict:
    """Flat, scalar-only per-disease row for the release history table."""
    return {
        "mondo": c.mondo, "label": c.label, "match_type": c.match_type,
        "n_hpoa_nodes": c.n_hpoa_nodes,
        "n_dismech": c.n_dismech, "n_hpoa": c.n_hpoa, "n_shared": c.n_shared,
        "n_novel": c.n_novel, "n_missing": c.n_missing,
        "more_specific": c.more_specific, "more_general": c.more_general,
        "exact_jaccard": c.exact.jaccard,
        "exact_dismech_in_hpoa": c.exact.precision,
        "exact_hpoa_in_dismech": c.exact.recall,
        "closure_jaccard": c.closure.jaccard,
        "closure_dismech_in_hpoa": c.closure.precision,
        "closure_hpoa_in_dismech": c.closure.recall,
        "resnik_bma": c.resnik_bma,
    }


def release_totals(res: Result) -> dict:
    """Flat per-release summary: coverage counts + micro/macro aggregates."""
    out = dict(res.coverage)
    for kind in ("exact", "closure"):
        for avg in ("micro", "macro"):
            for k, v in res.aggregates[kind][avg].items():
                out[f"{kind}_{avg}_{k}"] = v
    for k in ("total_novel", "total_missing", "more_specific", "more_general"):
        out[k] = res.aggregates[k]
    for k, v in res.frequency_summary.items():
        out[f"freq_{k}"] = v
    return out
