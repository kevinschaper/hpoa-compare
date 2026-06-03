# Methods

## What's being compared

- **dismech** — `phenotype.dismech.hpoa`, the HPOA-extended export from
  [monarch-initiative/dismech](https://github.com/monarch-initiative/dismech).
  MONDO-anchored; one row per (phenotype, evidence) pair.
- **HPOA** — HPO's gold-standard `phenotype.hpoa`. Keyed by OMIM / ORPHA /
  DECIPHER.

Both are pinned with version + sha256 in [`data/MANIFEST.yaml`](https://github.com/kevinschaper/hpoa-compare/blob/main/data/MANIFEST.yaml).

## Disease axis — MONDO SSSOM

dismech is MONDO; HPOA is not. Each dismech MONDO disease is resolved through
the MONDO SSSOM file via `skos:exactMatch` to its OMIM/Orphanet/DECIPHER
counterparts (`Orphanet:` → `ORPHA:`). When a MONDO term maps to several HPOA
disease IDs, we compare against the **union** of their HPOA annotations.

A disease is **comparable** only if at least one of its exact-match IDs is
actually present in HPOA.

## Phenotype axis — hierarchy-aware

Comparing exact HP IDs badly undercounts agreement, because dismech and HPOA
frequently annotate the same lineage at different depths. So the headline metric
expands both term sets to their **reflexive is-a closure**, capped at
`HP:0000118` (phenotypic abnormality), then computes precision / recall / F1 /
Jaccard on the closures. Exact-ID scores are reported alongside as a floor.

Closures and similarity come from a semantic-SQL build of HPO (`entailed_edge`
gives the transitive is-a closure directly).

### Term-level differences

- **Novel** (dismech only): a dismech term that is neither an ancestor nor a
  descendant of any HPOA term for that disease.
- **Missing** (HPOA only): the converse.
- **Specificity tilt**: among agreeing dismech terms, how many are strictly
  *below* a matching HPOA term (finer) vs strictly *above* it (coarser).

### Structure-based information content

The secondary Resnik best-match-average uses **structure-based IC**:
`−log₂(|descendants(t)| / |universe|)` over the phenotypic-abnormality subtree.
It's deliberately independent of either annotation corpus, so "agreement" isn't
biased toward HPOA's (or dismech's) term-frequency distribution.

## Scoping decisions

- Only `aspect = P` (phenotypic abnormality) HPOA rows; inheritance / clinical-course /
  modifier rows are excluded.
- Positive associations only for the overlap metrics; `NOT`-qualified rows are
  held aside for a future contradiction analysis.
- dismech's untyped `DISMECH:` synthetic CURIEs are excluded from term metrics
  (they have no HPO identity); the share that are HP-typed is reported as
  **term comparability**.
- dismech's MONDO-typed comorbidity sidecar is not part of `phenotype.hpoa` and
  is not compared.

## Caveats

- **Recall is structurally low**: HPOA is exhaustive per disease; dismech is
  curated-selective. Low recall is expected and is a property of intent, not an
  error — read precision and the novel/missing lists alongside it.
- Union-over-exactMatch can pool a broad MONDO grouping against several specific
  OMIM entries; the per-disease table shows the mapped IDs so this is visible.
