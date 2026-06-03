# Methods

## Vocabulary

Three units, kept distinct throughout:

- **disease** — a MONDO term (a card / row).
- **phenotype** — an HP term.
- **annotation** (disease–phenotype association) — the *pair* linking a disease to a
  phenotype; HPOA's fundamental row. dismech may carry several evidence rows per
  association.

Per-disease counts (`dismech` / `HPOA phenotypes`, novel, missing) are **phenotypes
for that one disease**. The pooled totals on [novel & missing](./diff) are
**associations** — the same phenotype recurs across many diseases, so they are not a
count of distinct phenotypes. Precision / recall / F1 are computed over a disease's
**phenotype set**.

## What's being compared

- **dismech** — `phenotype.dismech.hpoa`, the HPOA-extended export from
  [monarch-initiative/dismech](https://github.com/monarch-initiative/dismech).
  MONDO-anchored; one row per (phenotype, evidence) pair.
- **HPOA** — HPO's gold-standard `phenotype.hpoa`. Keyed by OMIM / ORPHA /
  DECIPHER.

Both are pinned with version + sha256 in [`data/MANIFEST.yaml`](https://github.com/kevinschaper/hpoa-compare/blob/main/data/MANIFEST.yaml).

## Disease axis — MONDO-centric

MONDO is the canonical disease space. dismech is natively MONDO; HPOA's
OMIM/ORPHA/DECIPHER diseases are **lifted up to MONDO** via the MONDO SSSOM
(`skos:exactMatch`, `Orphanet:` → `ORPHA:`). Several OMIM/ORPHA subtypes that
share a MONDO collapse onto it, their annotations **unioned**. Both sides then
live in MONDO space:

- **shared** — MONDO diseases with annotations on both sides (these are scored);
- **dismech-only** — dismech curation HPOA doesn't share at that MONDO node;
- **HPOA-only** — MONDO diseases HPOA characterizes but dismech hasn't.

dismech deliberately curates beyond OMIM/ORPHA (common, acquired, infectious
disease), so dismech-only is **coverage that extends HPOA**, not a deficiency.
See [disease coverage](./coverage).

### Disease-axis is-a matching

Matching is **MONDO is-a–aware**, mirroring the phenotype axis. Using the MONDO
graph from the release KGX (version-matched to the SSSOM; semsql lags — see
`MANIFEST.yaml`):

- **exact** — same MONDO node (these are the phenotype-scored set);
- **lineage** — an HPOA-annotated MONDO within **2 is-a hops** up or down, so a
  dismech grouping is reconciled with its near subtypes (and vice versa) but not
  its whole category. Phenotypes for a lineage match union the subtype
  annotations; the breadth (number of nodes rolled up) is reported, and these are
  kept **out of the headline phenotype averages** to avoid grouping distortion;
- **dismech-only / HPOA-only** — no MONDO relative within 2 hops.

**Obsolete resolution.** SSSOM mappings sometimes point an OMIM/ORPHA at an
*obsoleted* MONDO term; we redirect those to their `replaced_by` target so they
land on the live disease (e.g. HPOA's Dravet → obsolete `MONDO:0011794` →
`MONDO:0100135`, an exact match). The ontology root and non-disease groupings are
excluded.

**Limitations.** Lineage catches ancestor/descendant, not siblings; broad dismech
groupings still aggregate many subtypes (visible in the breadth column). A
common-ancestor / disease-similarity pass would address siblings — future work.

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
