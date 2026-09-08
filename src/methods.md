# Methods

## Two resources, not a benchmark

dismech and HPOA are **independently-built disease–phenotype resources** with
different goals, scope, and method. HPOA is the established HPO annotation set —
exhaustive per disease, derived from literature, registries and Orphanet, organized
around OMIM/Orphanet (rare-disease-centric). dismech is a newer, mechanism-driven,
MONDO-centric knowledge base — selective, focused on disease mechanism, and
extending to common and acquired disease beyond HPOA's scope.

Neither is treated as ground truth. This is a **symmetric comparison**: where they
overlap, and what each holds uniquely. A difference is a difference in approach, with
trade-offs on both sides — not an error in either. Accordingly the metrics are
order-free (Jaccard overlap) or reported in **both** directions, never as
"precision/recall against a gold standard."

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
count of distinct phenotypes. The overlap measures are computed over a disease's
**phenotype set**.

## What's being compared

- **dismech** — `phenotype.dismech.hpoa`, the HPOA-extended export from
  [monarch-initiative/dismech](https://github.com/monarch-initiative/dismech).
  MONDO-anchored; one row per (phenotype, evidence) pair.
- **HPOA** — HPO's established `phenotype.hpoa` annotation set. Keyed by OMIM / ORPHA /
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

Comparing exact HP IDs understates overlap, because the two resources frequently
annotate the same lineage at different depths. So the headline measure expands both
term sets to their **reflexive is-a closure**, capped at `HP:0000118` (phenotypic
abnormality), and reports overlap on the closures three ways:

- **Jaccard** — `|∩| / |∪|`, order-free overlap;
- **of dismech ⊂ HPOA** — the share of dismech's phenotypes also in HPOA;
- **of HPOA ⊂ dismech** — the share of HPOA's phenotypes also in dismech.

The two directional shares are deliberately asymmetric — they characterize how the
resources differ in breadth, not how well one matches the other. Exact-ID overlap is
reported alongside as a lower bound. Closures are the transitive `is_a` closure of
the release `hp.obo` (version-matched to `phenotype.hpoa`).

### Per-disease phenotype groups

- **In common**: phenotypes both resources assert (same HP id).
- **Unique to dismech**: a dismech phenotype that is neither an ancestor nor a
  descendant of any HPOA phenotype for that disease.
- **Unique to HPOA**: the converse.
- **Specificity tilt**: among phenotypes on a shared lineage, how many are strictly
  *finer* in dismech vs strictly *coarser*.

### Structure-based information content

The secondary Resnik best-match-average uses **structure-based IC**:
`−log₂(|descendants(t)| / |universe|)` over the phenotypic-abnormality subtree.
It's deliberately independent of either resource, so overlap isn't biased toward
either one's term-frequency distribution. (Note: this descendant-count IC saturates
for leaf terms, so the per-disease phenotype lists are ranked by **depth** instead.)

## Scoping decisions

- Only `aspect = P` (phenotypic abnormality) HPOA rows; inheritance / clinical-course /
  modifier rows are excluded.
- Positive associations only for the overlap measures; `NOT`-qualified rows are
  held aside for a future contradiction analysis.
- dismech's untyped `DISMECH:` synthetic CURIEs are excluded from phenotype-set
  measures (they have no HPO identity); the **phenotype-typed** share is reported.
- dismech's MONDO-typed comorbidity sidecar is not part of `phenotype.hpoa` and
  is not compared.
- **Frequency** ([frequency](./frequency)): where both resources assert the same
  phenotype, each side's frequency (HP term / percentage / `n/m` ratio) is flattened
  to one of the six HP frequency bands and the bands are compared. Done on shared
  phenotypes of exact disease matches only (lineage matches aggregate subtype
  frequencies). HPOA's frequency is the modal band across the OMIM/ORPHA ids that
  lift to a MONDO. Caveat: small-cohort ratios (`1/1` → Obligate) can overstate the
  extremes.

## Release history

The [over time](./history) page repeats the comparison for every dismech release.

- **Snapshot** — one dismech release tag paired with the **newest HPO release on or
  before the tag's commit date**. dismech releases roughly weekly and HPO every few
  months, so the timeline is keyed by dismech release and HPO changes appear as
  steps (marked on the charts).
- **dismech per tag** — dismech releases do not ship `phenotype.dismech.hpoa`, but
  the exporter is a pure projection of the `kb/disorders` YAML, so the *current*
  exporter is run against each tag's knowledge base (`scripts/export_dismech_tags.sh`).
- **Fixed axes** — the MONDO SSSOM, MONDO graph, obsolete map and `hp.obo` are held
  at their current release for every snapshot. The series therefore measure
  *annotation* change, not ontology drift; a MONDO or HPO update can still move
  every point when the history is rebuilt, which is why per-release results carry
  the fingerprint of the fixed inputs and are recomputed when it changes.
- **What is tracked** — per release: the coverage counts and pooled overlap
  measures above; per disease and release: phenotype counts on each side, in
  common / unique to each, the exact and hierarchy-aware overlap measures, and
  Resnik. Term-level lists are kept for the current release only. HPOA-only
  diseases are counted per release but not tracked individually.
- **Storage** — per-release results are Parquet files committed under
  `data/history/`, combined with DuckDB into one `history.parquet` that the page
  queries in the browser with DuckDB-Wasm.

## Caveats

- **The two resources differ in breadth by design.** HPOA is exhaustive per
  disease; dismech is selective and mechanism-focused. So "of HPOA ⊂ dismech" is
  low and "of dismech ⊂ HPOA" is high — this is the signature of a selective
  resource beside an exhaustive one, not a quality judgement on either.
- Union-over-exactMatch can pool a broad MONDO grouping against several specific
  OMIM entries; the per-disease cards show the mapped IDs so this is visible.
