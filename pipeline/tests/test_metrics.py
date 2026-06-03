"""Unit tests for the comparison metrics using a tiny stub ontology."""
import pytest

from hpoa_compare import metrics


class StubHpo:
    """Linear chain A > B > C (A is the most general), plus an isolated X."""

    _parent = {"C": "B", "B": "A", "A": None, "X": None}

    def _anc(self, t):
        out, cur = set(), t
        while cur is not None:
            out.add(cur)
            cur = self._parent.get(cur)
        return out

    def ancestors(self, t):
        return frozenset(self._anc(t))

    def descendants(self, t):
        return {d for d in self._parent if t in self._anc(d)}

    def closure(self, terms):
        out = set()
        for t in terms:
            out |= self._anc(t)
        return out

    def ic(self, t):
        return {"A": 0.0, "B": 1.0, "C": 2.0, "X": 2.0}[t]

    def mica_ic(self, a, b):
        common = self.ancestors(a) & self.ancestors(b)
        return max((self.ic(c) for c in common), default=0.0)

    def label(self, t):
        return f"label-{t}"


@pytest.fixture
def hpo():
    return StubHpo()


def test_exact_vs_closure_lift(hpo):
    # dismech says C (specific), HPOA says B (its parent): exact miss, closure hit.
    c = metrics.compare_disease("MONDO:1", "d", ["OMIM:1"], {"C"}, {"B"}, hpo)
    assert c.exact.tp == 0
    assert c.closure.tp > 0  # B is in closure({C}) = {C,B,A}
    assert c.closure.f1 > c.exact.f1


def test_novel_term_has_no_lineage_match(hpo):
    # X shares no ancestor/descendant with the HPOA set {B}.
    c = metrics.compare_disease("MONDO:1", "d", ["OMIM:1"], {"X"}, {"B"}, hpo)
    assert c.n_novel == 1
    assert c.novel_terms[0]["id"] == "X"


def test_specificity_tilt(hpo):
    # dismech C is strictly below HPOA B -> finer.
    c = metrics.compare_disease("MONDO:1", "d", ["OMIM:1"], {"C"}, {"B"}, hpo)
    assert c.more_specific == 1
    assert c.more_general == 0


def test_missing_term_has_no_lineage_match(hpo):
    # dismech B agrees with C (ancestor); X shares no lineage with B -> missing.
    c = metrics.compare_disease("MONDO:1", "d", ["OMIM:1"], {"B"}, {"C", "X"}, hpo)
    assert c.n_novel == 0
    assert c.n_missing == 1
    assert c.missing_terms[0]["id"] == "X"
