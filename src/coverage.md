# Disease coverage

Both sides are placed in **MONDO space** (HPOA's OMIM/ORPHA/DECIPHER diseases are
lifted up to MONDO via `skos:exactMatch`), then we ask: which MONDO diseases does
each side cover? dismech is intentionally MONDO-centric, so curation that extends
beyond OMIM/ORPHA is coverage to celebrate, not a mapping failure.

```js
const coverage = await FileAttachment("data/coverage.json").json();
const dc = await FileAttachment("data/disease_coverage.json").json();
```

<div class="grid grid-cols-3">
  <div class="card">
    <h2>Shared</h2>
    <span class="big">${coverage.comparable.toLocaleString()}</span>
    MONDO diseases on both sides
  </div>
  <div class="card">
    <h2>dismech-only</h2>
    <span class="big">${coverage.dismech_only.toLocaleString()}</span>
    of which ${coverage.dismech_only_beyond_omim_orpha} have no direct OMIM/ORPHA xref
  </div>
  <div class="card">
    <h2>HPOA-only (gaps)</h2>
    <span class="big">${coverage.hpoa_only.toLocaleString()}</span>
    MONDO diseases dismech hasn't curated yet
  </div>
</div>

```js
const flow = [
  {side: `dismech (${coverage.dismech_diseases})`, seg: "shared", n: coverage.comparable},
  {side: `dismech (${coverage.dismech_diseases})`, seg: "dismech-only", n: coverage.dismech_only},
  {side: `HPOA→MONDO (${coverage.hpoa_diseases_mondo})`, seg: "shared", n: coverage.comparable},
  {side: `HPOA→MONDO (${coverage.hpoa_diseases_mondo})`, seg: "HPOA-only", n: coverage.hpoa_only},
];
```

```js
Plot.plot({
  width,
  marginLeft: 160,
  x: {label: "MONDO diseases →"},
  y: {label: null},
  color: {legend: true, domain: ["shared", "dismech-only", "HPOA-only"], range: ["#4269d0", "#3ca951", "#9aa7b4"]},
  marks: [
    Plot.barX(flow, {y: "side", x: "n", fill: "seg", order: ["shared", "dismech-only", "HPOA-only"]}),
    Plot.text(flow, {y: "side", x: "n", text: (d) => d.n.toLocaleString(), fill: "seg", dx: 14, textAnchor: "start"}),
    Plot.ruleX([0]),
  ],
})
```

HPOA is far larger in raw disease count — it's an exhaustive rare-disease resource —
so the gap bar dwarfs dismech. The point isn't to match its breadth but to see
*where dismech extends it* and *which well-characterized diseases are still open*.

<div class="note">

**Caveat — MONDO grouping granularity.** "No direct OMIM/ORPHA xref" is not the
same as "novel disease." Some dismech-only entries are MONDO *grouping* terms
(e.g. Dravet syndrome, spinal muscular atrophy) whose `exactMatch` targets are
DOID/NCIT/ICD rather than OMIM/ORPHA, while HPOA annotates a *child* MONDO. A
MONDO is-a–closure pass on the disease axis (mirroring the phenotype-axis
hierarchy treatment) would reconcile these — a planned refinement.

</div>

## Where dismech extends HPOA

dismech-curated MONDO diseases with no HPOA annotations at the same MONDO node.
**direct xref = yes** means HPOA recognizes the disease (an OMIM/ORPHA exists) but
hasn't characterized it — dismech is adding phenotype coverage; **no** means the
MONDO term has no direct OMIM/ORPHA match (genuinely beyond, or grouping-level).

```js
const dismechOnly = dc.dismech_only.map((r) => ({
  disease: r.label,
  mondo: r.mondo,
  terms: r.n_terms,
  directXref: r.beyond_omim_orpha ? "no" : "yes",
}));
const onlySearch = view(Inputs.search(dismechOnly, {placeholder: "search dismech-only diseases…"}));
```

```js
Inputs.table(onlySearch, {
  sort: "terms",
  reverse: true,
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
  },
  width: {disease: 300},
})
```

## Coverage gaps — what dismech isn't covering yet

MONDO diseases HPOA characterizes but dismech hasn't, ranked by HPOA annotation
richness (most-characterized first) — a prioritized curation backlog.

```js
const gaps = dc.hpoa_only.map((r) => ({
  disease: r.label,
  mondo: r.mondo,
  hpoaTerms: r.n_terms,
  sources: r.hpoa_ids.join(", "),
}));
const gapSearch = view(Inputs.search(gaps, {placeholder: "search coverage gaps…"}));
```

```js
Inputs.table(gapSearch, {
  sort: "hpoaTerms",
  reverse: true,
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
  },
  width: {disease: 300},
})
```
