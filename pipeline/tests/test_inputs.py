"""Input parsing + release pairing."""
from hpoa_compare import load
from hpoa_compare.cli import pair_hpoa_release
from hpoa_compare.hpo import HpoGraph

OBO = """format-version: 1.2
data-version: hp/releases/2026-09-01

[Term]
id: HP:0000001
name: All

[Term]
id: HP:0000118
name: Phenotypic abnormality
is_a: HP:0000001 ! All

[Term]
id: HP:0000002
name: Mode of inheritance
is_a: HP:0000001 ! All

[Term]
id: HP:0000010
name: Nervous system
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0000011
name: Seizure
is_a: HP:0000010 ! Nervous system

[Term]
id: HP:0000012
name: Old seizure
is_obsolete: true
is_a: HP:0000010 ! Nervous system
"""


def test_hpo_graph_from_obo(tmp_path):
    p = tmp_path / "hp.obo"
    p.write_text(OBO)
    g = HpoGraph(p)
    assert g.version == "hp/releases/2026-09-01"
    # universe = phenotypic-abnormality subtree only; obsolete terms dropped
    assert g.universe == {"HP:0000118", "HP:0000010", "HP:0000011"}
    assert g.ancestors("HP:0000011") == {"HP:0000011", "HP:0000010", "HP:0000118"}
    assert g.descendants("HP:0000010") == {"HP:0000010", "HP:0000011"}
    assert g.depth("HP:0000011") == 2
    assert g.ic("HP:0000118") == 0.0 and g.ic("HP:0000011") > g.ic("HP:0000010")
    assert g.label("HP:0000011") == "Seizure"
    assert g.mica_ic("HP:0000011", "HP:0000010") == g.ic("HP:0000010")


def test_read_header(tmp_path):
    p = tmp_path / "x.hpoa"
    p.write_text("#description: x [1: a; 2: b]\n#version: 2026-09-02\ndatabase_id\tdisease_name\n")
    h = load.read_header(p)
    assert h["version"] == "2026-09-02"
    assert h["description"].startswith("x")


def test_pair_hpoa_release():
    rel = ["2025-11-24", "2026-01-08", "2026-02-16"]
    assert pair_hpoa_release("2025-12-12", rel) == "2025-11-24"
    assert pair_hpoa_release("2026-01-08", rel) == "2026-01-08"
    assert pair_hpoa_release("2026-05-01", rel) == "2026-02-16"
    assert pair_hpoa_release("2025-01-01", rel) == "2025-11-24"  # nothing older: oldest
