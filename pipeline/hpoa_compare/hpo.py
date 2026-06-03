"""HPO ontology access: transitive is-a closure and structure-based IC.

Reads a semantic-SQL (semsql) build of HPO (``hp.db``). The ``entailed_edge``
table already holds the transitive is-a closure, so ancestors/descendants are a
single indexed lookup rather than a graph walk.

All closures are restricted to the *phenotypic abnormality* subtree
(descendants of HP:0000118) so that:

* ancestor closures stop at HP:0000118 instead of climbing into ``owl:Thing``,
  which would let the root dominate every overlap;
* information content is computed over a coherent universe of phenotype terms.
"""
from __future__ import annotations

import math
import sqlite3
from functools import cached_property
from pathlib import Path

IS_A = "rdfs:subClassOf"
PHENOTYPIC_ABNORMALITY = "HP:0000118"


class HpoGraph:
    def __init__(self, db_path: str | Path):
        self.con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self._anc: dict[str, set[str]] = {}
        self._desc: dict[str, set[str]] = {}
        self._load_edges()
        self._precompute()

    def _load_edges(self) -> None:
        cur = self.con.execute(
            "SELECT subject, object FROM entailed_edge "
            "WHERE predicate = ? AND subject LIKE 'HP:%' AND object LIKE 'HP:%'",
            (IS_A,),
        )
        for subj, obj in cur:
            # entailed_edge is reflexive+transitive: subject is-a* object.
            self._anc.setdefault(subj, set()).add(obj)
            self._desc.setdefault(obj, set()).add(subj)

    def _precompute(self) -> None:
        """Pin the universe, ancestor frozensets, and structure-based IC up front
        so per-pair similarity is dict lookups rather than repeated set algebra."""
        u = self._desc.get(PHENOTYPIC_ABNORMALITY, set()) | {PHENOTYPIC_ABNORMALITY}
        self.universe: frozenset[str] = frozenset(u)
        n = len(u)
        self._anc_u: dict[str, frozenset[str]] = {}
        self._ic: dict[str, float] = {}
        for t in u:
            self._anc_u[t] = frozenset((self._anc.get(t, set()) | {t}) & u)
            n_desc = len((self._desc.get(t, set()) | {t}) & u)
            self._ic[t] = -math.log2(n_desc / n) if n_desc else 0.0

    def ancestors(self, term: str) -> frozenset[str]:
        """Reflexive ancestors of ``term`` within the phenotype universe."""
        return self._anc_u.get(term, frozenset({term} & self.universe))

    def descendants(self, term: str) -> set[str]:
        """Reflexive descendants of ``term`` within the phenotype universe."""
        return (self._desc.get(term, set()) | {term}) & self.universe

    def closure(self, terms: set[str]) -> set[str]:
        """Union of reflexive ancestor closures (is-a, capped at HP:0000118)."""
        out: set[str] = set()
        for t in terms:
            out |= self.ancestors(t)
        return out

    def ic(self, term: str) -> float:
        """Structure-based information content: -log2(|descendants| / |universe|).

        Independent of any annotation corpus, so it does not bias 'agreement'
        toward either dismech's or HPOA's term-frequency distribution.
        """
        return self._ic.get(term, 0.0)

    def mica_ic(self, t1: str, t2: str) -> float:
        """IC of the most-informative common ancestor of two terms."""
        common = self.ancestors(t1) & self.ancestors(t2)
        return max((self._ic.get(a, 0.0) for a in common), default=0.0)

    @cached_property
    def labels(self) -> dict[str, str]:
        cur = self.con.execute(
            "SELECT subject, value FROM rdfs_label_statement WHERE subject LIKE 'HP:%'"
        )
        return {s: v for s, v in cur}

    def label(self, term: str) -> str:
        return self.labels.get(term, term)
