"""Hierarchy-aware comparison metrics for two disease->term annotation sets.

Headline metric is ancestor-closure precision/recall/F1: expand both term sets
to their reflexive is-a closure (capped at HP:0000118) and compare. This gives
graded partial credit when dismech and HPOA annotate at different levels of the
same lineage. Exact-ID metrics are kept as a floor to contrast against.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .hpo import HpoGraph


@dataclass
class SetScore:
    tp: int
    n_pred: int   # dismech
    n_gold: int   # hpoa
    precision: float
    recall: float
    f1: float
    jaccard: float


def _score(pred: set[str], gold: set[str]) -> SetScore:
    tp = len(pred & gold)
    union = len(pred | gold)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(gold) if gold else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    j = tp / union if union else 0.0
    return SetScore(tp, len(pred), len(gold), round(p, 4), round(r, 4), round(f1, 4), round(j, 4))


@dataclass
class DiseaseComparison:
    mondo: str
    label: str
    hpoa_ids: list[str]
    match_type: str          # exact | descendant | ancestor | mixed (MONDO lineage)
    n_hpoa_nodes: int        # how many HPOA-annotated MONDO nodes were aggregated
    n_dismech: int
    n_hpoa: int
    exact: SetScore
    closure: SetScore
    n_shared: int           # phenotypes in both (exact HP id)
    n_novel: int            # dismech terms with no ancestor/descendant in HPOA
    n_missing: int          # HPOA terms with no ancestor/descendant in dismech
    more_specific: int      # dismech terms strictly below a matching HPOA term
    more_general: int       # dismech terms strictly above a matching HPOA term
    resnik_bma: float       # symmetric best-match-average MICA information content
    shared_terms: list[dict] = field(default_factory=list)
    novel_terms: list[dict] = field(default_factory=list)
    missing_terms: list[dict] = field(default_factory=list)

    def to_row(self) -> dict:
        d = asdict(self)
        d["exact"] = asdict(self.exact)
        d["closure"] = asdict(self.closure)
        return d


def _agrees(term: str, others: set[str], hpo: HpoGraph) -> bool:
    """True if ``term`` is an ancestor or descendant of any term in ``others``."""
    anc = hpo.ancestors(term)
    desc = hpo.descendants(term)
    return any(o in anc or o in desc for o in others)


def _resnik_bma(pred: set[str], gold: set[str], hpo: HpoGraph) -> float:
    if not pred or not gold:
        return 0.0
    p2g = sum(max(hpo.mica_ic(p, g) for g in gold) for p in pred) / len(pred)
    g2p = sum(max(hpo.mica_ic(g, p) for p in pred) for g in gold) / len(gold)
    return round((p2g + g2p) / 2, 4)


def compare_disease(
    mondo: str,
    label: str,
    hpoa_ids: list[str],
    dismech_terms: set[str],
    hpoa_terms: set[str],
    hpo: HpoGraph,
    *,
    match_type: str = "exact",
    n_hpoa_nodes: int = 1,
    keep_diffs: bool = True,
    diff_cap: int = 25,
) -> DiseaseComparison:
    exact = _score(dismech_terms, hpoa_terms)
    closure = _score(hpo.closure(dismech_terms), hpo.closure(hpoa_terms))

    shared = dismech_terms & hpoa_terms
    novel = {t for t in dismech_terms if not _agrees(t, hpoa_terms, hpo)}
    missing = {t for t in hpoa_terms if not _agrees(t, dismech_terms, hpo)}

    more_specific = more_general = 0
    for t in dismech_terms - novel:
        anc, desc = hpo.ancestors(t) - {t}, hpo.descendants(t) - {t}
        if hpoa_terms & anc:      # an HPOA term is an ancestor -> dismech is finer
            more_specific += 1
        elif hpoa_terms & desc:   # an HPOA term is a descendant -> dismech is coarser
            more_general += 1

    def _terms(ids: set[str]) -> list[dict]:
        # Rank by depth (longest is-a path), not descendant-count IC: every leaf
        # has 1 descendant and so saturates at the same max IC, which makes IC
        # useless for ordering the (leaf-heavy) novel/missing lists.
        ranked = sorted(
            ({"id": t, "label": hpo.label(t), "depth": hpo.depth(t)} for t in ids),
            key=lambda x: (-x["depth"], x["id"]),  # id tiebreaker -> deterministic
        )
        return ranked[:diff_cap]  # full counts live in n_novel / n_missing

    return DiseaseComparison(
        mondo=mondo,
        label=label,
        hpoa_ids=sorted(hpoa_ids),
        match_type=match_type,
        n_hpoa_nodes=n_hpoa_nodes,
        n_dismech=len(dismech_terms),
        n_hpoa=len(hpoa_terms),
        exact=exact,
        closure=closure,
        n_shared=len(shared),
        n_novel=len(novel),
        n_missing=len(missing),
        more_specific=more_specific,
        more_general=more_general,
        resnik_bma=_resnik_bma(dismech_terms, hpoa_terms, hpo),
        shared_terms=_terms(shared) if keep_diffs else [],
        novel_terms=_terms(novel) if keep_diffs else [],
        missing_terms=_terms(missing) if keep_diffs else [],
    )


def micro_average(comparisons: list[DiseaseComparison], attr: str) -> dict:
    """Pool counts across diseases for a SetScore attribute ('exact'|'closure').

    Reported symmetrically: ``jaccard`` is the order-free overlap; ``dismech_in_hpoa``
    and ``hpoa_in_dismech`` are the two directional shares (neither is a 'precision'
    or 'recall' against a gold standard — HPOA is not ground truth).
    """
    tp = sum(getattr(c, attr).tp for c in comparisons)
    n_dismech = sum(getattr(c, attr).n_pred for c in comparisons)
    n_hpoa = sum(getattr(c, attr).n_gold for c in comparisons)
    union = n_dismech + n_hpoa - tp
    return {
        "jaccard": round(tp / union, 4) if union else 0.0,
        "dismech_in_hpoa": round(tp / n_dismech, 4) if n_dismech else 0.0,
        "hpoa_in_dismech": round(tp / n_hpoa, 4) if n_hpoa else 0.0,
    }


def macro_average(comparisons: list[DiseaseComparison], attr: str) -> dict:
    n = len(comparisons) or 1
    return {
        "jaccard": round(sum(getattr(c, attr).jaccard for c in comparisons) / n, 4),
        "dismech_in_hpoa": round(sum(getattr(c, attr).precision for c in comparisons) / n, 4),
        "hpoa_in_dismech": round(sum(getattr(c, attr).recall for c in comparisons) / n, 4),
    }
