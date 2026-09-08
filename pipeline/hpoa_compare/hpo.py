"""HPO ontology access: transitive is-a closure and structure-based IC.

Reads the release ``hp.obo`` (shipped with every HPO release alongside
``phenotype.hpoa``, so the phenotype graph is version-matched to the annotations).
Ancestors/descendants are the memoized transitive closure over direct ``is_a``.

All closures are restricted to the *phenotypic abnormality* subtree
(descendants of HP:0000118) so that:

* ancestor closures stop at HP:0000118 instead of climbing into ``owl:Thing``,
  which would let the root dominate every overlap;
* information content is computed over a coherent universe of phenotype terms.
"""
from __future__ import annotations

import math
from pathlib import Path

PHENOTYPIC_ABNORMALITY = "HP:0000118"


def parse_obo(path: str | Path) -> tuple[dict[str, set[str]], dict[str, str], str]:
    """Return ``(parents, labels, data_version)`` for non-obsolete HP terms.

    Only ``id``, ``name``, ``is_a`` and ``is_obsolete`` are read; everything else
    in the OBO is ignored.
    """
    parents: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    version = ""
    cur: str | None = None
    cur_parents: set[str] = set()
    cur_label = ""
    obsolete = False

    def flush() -> None:
        if cur and not obsolete:
            parents[cur] = cur_parents
            labels[cur] = cur_label or cur

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("data-version:"):
                version = line.split(":", 1)[1].strip()
            elif line == "[Term]":
                flush()
                cur, cur_parents, cur_label, obsolete = None, set(), "", False
            elif line.startswith("[") and line.endswith("]"):
                flush()
                cur = None
            elif cur is None and line.startswith("id: HP:"):
                cur = line[4:].strip()
            elif cur and line.startswith("name: "):
                cur_label = line[6:].strip()
            elif cur and line.startswith("is_a: HP:"):
                cur_parents.add(line[6:].split("!")[0].strip())
            elif cur and line.startswith("is_obsolete: true"):
                obsolete = True
        flush()
    return parents, labels, version


class HpoGraph:
    def __init__(self, obo_path: str | Path):
        self._parents, self.labels, self.version = parse_obo(obo_path)
        self._children: dict[str, set[str]] = {}
        for child, ps in self._parents.items():
            for p in ps:
                self._children.setdefault(p, set()).add(child)
        self._anc_cache: dict[str, frozenset[str]] = {}
        self._desc_cache: dict[str, frozenset[str]] = {}
        self._depth_cache: dict[str, int] = {}
        self._precompute()

    def _closure(self, term: str, adjacency: dict[str, set[str]],
                 cache: dict[str, frozenset[str]]) -> frozenset[str]:
        if term in cache:
            return cache[term]
        cache[term] = frozenset({term})  # cycle guard
        acc: set[str] = {term}
        for nxt in adjacency.get(term, ()):
            acc |= self._closure(nxt, adjacency, cache)
        out = frozenset(acc)
        cache[term] = out
        return out

    def _precompute(self) -> None:
        """Pin the universe, ancestor frozensets, and structure-based IC up front
        so per-pair similarity is dict lookups rather than repeated set algebra."""
        u = self._closure(PHENOTYPIC_ABNORMALITY, self._children, self._desc_cache)
        self.universe: frozenset[str] = u
        n = len(u)
        self._anc_u: dict[str, frozenset[str]] = {}
        self._ic: dict[str, float] = {}
        for t in u:
            self._anc_u[t] = self._closure(t, self._parents, self._anc_cache) & u
            n_desc = len(self._closure(t, self._children, self._desc_cache) & u)
            self._ic[t] = -math.log2(n_desc / n) if n_desc else 0.0

    def ancestors(self, term: str) -> frozenset[str]:
        """Reflexive ancestors of ``term`` within the phenotype universe."""
        return self._anc_u.get(term, frozenset({term} & self.universe))

    def descendants(self, term: str) -> set[str]:
        """Reflexive descendants of ``term`` within the phenotype universe."""
        if term not in self.universe:
            return set()
        return set(self._closure(term, self._children, self._desc_cache) & self.universe)

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

    def depth(self, term: str) -> int:
        """Longest is-a path from HP:0000118 (specificity that discriminates leaves,
        unlike descendant-count IC which saturates at the max for every leaf)."""
        if term == PHENOTYPIC_ABNORMALITY or term not in self.universe:
            return 0
        cached = self._depth_cache.get(term)
        if cached is not None:
            return cached
        self._depth_cache[term] = 0  # cycle guard
        parents = self._parents.get(term, set()) & self.universe
        d = 1 + max((self.depth(p) for p in parents), default=-1)
        self._depth_cache[term] = d
        return d

    def label(self, term: str) -> str:
        return self.labels.get(term, term)
