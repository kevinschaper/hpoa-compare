"""MONDO disease-axis is-a graph from the release KGX artifacts.

We deliberately do NOT use the semsql ``mondo.db`` here: it lags the OBO release
(see data/MANIFEST.yaml). The KGX ``mondo_edges.tsv`` / ``mondo_nodes.tsv`` from
the same release as the SSSOM give the freshest, version-matched MONDO graph.

Edges are direct ``biolink:subclass_of`` between MONDO terms; ancestors and
descendants are the memoized transitive closure over them. This lets a dismech
*grouping* disease be reconciled with HPOA annotations on its *subtype* MONDOs.
"""
from __future__ import annotations

import csv
from pathlib import Path

SUBCLASS = "biolink:subclass_of"


class MondoGraph:
    def __init__(self, edges_path: str | Path, nodes_path: str | Path):
        self._parents: dict[str, set[str]] = {}
        self._children: dict[str, set[str]] = {}
        self._labels: dict[str, str] = {}
        self._deprecated: set[str] = set()
        self._anc_cache: dict[str, frozenset[str]] = {}
        self._desc_cache: dict[str, frozenset[str]] = {}
        self._load_nodes(nodes_path)
        self._load_edges(edges_path)

    def _load_nodes(self, path: str | Path) -> None:
        with open(path, newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                node = row.get("id", "")
                if not node.startswith("MONDO:"):
                    continue
                self._labels[node] = row.get("name", node)
                if (row.get("deprecated") or "").strip().lower() in {"true", "1"}:
                    self._deprecated.add(node)

    def _load_edges(self, path: str | Path) -> None:
        with open(path, newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row.get("predicate") != SUBCLASS:
                    continue
                child, parent = row.get("subject", ""), row.get("object", "")
                if not (child.startswith("MONDO:") and parent.startswith("MONDO:")):
                    continue
                self._parents.setdefault(child, set()).add(parent)
                self._children.setdefault(parent, set()).add(child)

    def _closure(self, term: str, adjacency: dict[str, set[str]],
                 cache: dict[str, frozenset[str]]) -> frozenset[str]:
        if term in cache:
            return cache[term]
        cache[term] = frozenset({term})  # guard against cycles
        acc: set[str] = {term}
        for nxt in adjacency.get(term, ()):  # iterative-ish via recursion + memo
            acc |= self._closure(nxt, adjacency, cache)
        out = frozenset(acc)
        cache[term] = out
        return out

    def ancestors(self, term: str) -> frozenset[str]:
        """Reflexive is-a ancestors (more general)."""
        return self._closure(term, self._parents, self._anc_cache)

    def descendants(self, term: str) -> frozenset[str]:
        """Reflexive is-a descendants (more specific / subtypes)."""
        return self._closure(term, self._children, self._desc_cache)

    def _bounded(self, term: str, adjacency: dict[str, set[str]], max_hops: int) -> set[str]:
        """Reflexive neighborhood reachable within ``max_hops`` is-a steps."""
        seen = {term}
        frontier = {term}
        for _ in range(max_hops):
            nxt: set[str] = set()
            for t in frontier:
                nxt |= adjacency.get(t, set())
            nxt -= seen
            if not nxt:
                break
            seen |= nxt
            frontier = nxt
        return seen

    def ancestors_within(self, term: str, max_hops: int) -> set[str]:
        """Reflexive ancestors no more than ``max_hops`` steps up."""
        return self._bounded(term, self._parents, max_hops)

    def descendants_within(self, term: str, max_hops: int) -> set[str]:
        """Reflexive descendants no more than ``max_hops`` steps down."""
        return self._bounded(term, self._children, max_hops)

    def label(self, term: str) -> str:
        return self._labels.get(term, term)

    def is_obsolete(self, term: str) -> bool:
        return term in self._deprecated
