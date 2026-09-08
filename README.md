# hpoa-compare

Hierarchy-aware, **symmetric** comparison of two independently-built
disease–phenotype resources: [dismech](https://github.com/monarch-initiative/dismech)'s
`phenotype.dismech.hpoa` export and HPO's established `phenotype.hpoa`. Reconciled on
the disease axis through MONDO SSSOM and rendered as a static
[Observable Framework](https://observablehq.com/framework/) site.

**Live site:** <https://kevinschaper.github.io/hpoa-compare/>

Neither resource is treated as ground truth — the goal is to characterize where they
overlap and what each holds uniquely, not to score dismech against HPOA.

## What it measures

- **Coverage** — which MONDO diseases each resource covers (shared, dismech-only,
  HPOA-only), MONDO is-a–aware.
- **Overlap** — exact-ID vs **ancestor-closure** Jaccard plus the two directional
  shares (*of dismech ⊂ HPOA*, *of HPOA ⊂ dismech*), and a structure-IC Resnik
  best-match-average. Closure credits agreement anywhere along an is-a lineage.
- **Per disease** — phenotypes in common, unique to dismech, and unique to HPOA;
  whether dismech trends finer or coarser.
- **Over time** — the same comparison for every dismech release tag (paired with
  the contemporary HPO release): set sizes, overlap, and per-disease trajectories,
  queried in the browser with DuckDB-Wasm.

See [`src/methods.md`](src/methods.md) for the framing, methodology, and scoping.

## Layout

```
data/MANIFEST.yaml        pinned inputs (versions + sha256)
data/inputs/              downloaded inputs (gitignored):
  hpoa/<release>/           one phenotype.hpoa per HPO release
  dismech/<tag>/            one phenotype.dismech.hpoa per dismech release tag
data/history/             per-release comparison results (parquet + json, committed)
pipeline/hpoa_compare/    Python: load, SSSOM mapping, HPO closure/IC, metrics, compare
scripts/                  export_dismech_tags.sh (regenerate dismech per tag), helpers
src/                      Observable Framework site (pages + generated data/)
```

The Python pipeline does all the heavy lifting and emits tidy JSON (plus one
Parquet table for the release history) into `src/data/`; the site is a thin
rendering layer. `compare.py` runs one dismech-vs-HPOA comparison; `build` runs
it on the current pair and `history` on every release, caching each release's
result under `data/history/` so a refresh only computes what's new. DuckDB stacks
the per-release Parquet files, and the site queries the result with DuckDB-Wasm.

## Usage

```bash
just fetch              # MONDO (SSSOM + KGX graph), hp.obo, and every HPO release in the history
just export-dismech     # regenerate phenotype.dismech.hpoa for each dismech tag (sibling checkout)
just build              # compare the current pair -> src/data/*.json
just history            # compare every release -> src/data/history.parquet (+ per-release cache)
just dev                # preview the site locally (npm + Observable Framework)
just site               # build the static site to dist/
just test               # python unit tests
```

To add a new release: `just export-dismech` picks up new dismech tags; add any new
HPO release to `hpo_releases` in the justfile and re-run `just fetch`; then
`just build history` and commit `src/data/` + `data/history/`. CI only renders.

## Reproducibility

Inputs are pinned in `data/MANIFEST.yaml` (URL + version + sha256). The dismech
export is generated per release tag by `dismech.export.hpoa_export` (see
`scripts/export_dismech_tags.sh`); `data/inputs/dismech/tags.tsv` records the tag,
date and commit. The MONDO and HPO graphs are held fixed at their current release
across the whole history so the series measure annotation change, not ontology
drift; each cached release carries a fingerprint of those fixed inputs and is
recomputed when they change.
