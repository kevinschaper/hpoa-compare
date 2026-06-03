# Disease coverage

Both sides live in **MONDO space** (HPOA's OMIM/ORPHA/DECIPHER diseases lifted up
via `skos:exactMatch`, obsolete targets resolved to their replacements). Matching
is **MONDO is-a–aware**: a dismech grouping disease covers HPOA annotations on its
subtype MONDO nodes within a bounded distance — the disease-axis analogue of the
phenotype-axis closure.

```js
const coverage = await FileAttachment("data/coverage.json").json();
const dc = await FileAttachment("data/disease_coverage.json").json();
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Exact-shared</h2>
    <span class="big">${coverage.exact_shared.toLocaleString()}</span>
    same MONDO node — phenotype-scored
  </div>
  <div class="card">
    <h2>Lineage-shared</h2>
    <span class="big">${coverage.lineage_shared.toLocaleString()}</span>
    dismech grouping ↔ HPOA subtype (≤2 hops)
  </div>
  <div class="card">
    <h2>dismech-only</h2>
    <span class="big">${coverage.dismech_only.toLocaleString()}</span>
    ${coverage.dismech_only_beyond_omim_orpha} with no OMIM/ORPHA xref
  </div>
  <div class="card">
    <h2>Unique to HPOA</h2>
    <span class="big">${coverage.hpoa_only.toLocaleString()}</span>
    no dismech disease within 2 hops
  </div>
</div>

```js
const flow = [
  {side: `dismech (${coverage.dismech_diseases})`, seg: "exact-shared", n: coverage.exact_shared},
  {side: `dismech (${coverage.dismech_diseases})`, seg: "lineage-shared", n: coverage.lineage_shared},
  {side: `dismech (${coverage.dismech_diseases})`, seg: "dismech-only", n: coverage.dismech_only},
  {side: `HPOA→MONDO (${coverage.hpoa_diseases_mondo})`, seg: "exact-shared", n: coverage.exact_shared},
  {side: `HPOA→MONDO (${coverage.hpoa_diseases_mondo})`, seg: "lineage-covered", n: coverage.hpoa_lineage_covered},
  {side: `HPOA→MONDO (${coverage.hpoa_diseases_mondo})`, seg: "HPOA-only", n: coverage.hpoa_only},
];
const order = ["exact-shared", "lineage-shared", "lineage-covered", "dismech-only", "HPOA-only"];
```

```js
Plot.plot({
  width,
  marginLeft: 170,
  x: {label: "MONDO diseases →"},
  y: {label: null},
  color: {legend: true, domain: order, range: ["#4269d0", "#3ca951", "#97cda3", "#efb118", "#9aa7b4"]},
  marks: [
    Plot.barX(flow, {y: "side", x: "n", fill: "seg", order}),
    Plot.text(flow, {y: "side", x: "n", text: (d) => d.n.toLocaleString(), fill: "seg", dx: 14, textAnchor: "start"}),
    Plot.ruleX([0]),
  ],
})
```

HPOA is far larger in raw disease count — it's an exhaustive rare-disease resource —
so the gap bar dwarfs dismech. The point isn't to match its breadth but to see
*where dismech extends it* and *which well-characterized diseases are still open*.

<div class="note">

**How matching works.** Exact = same MONDO node. Lineage = an HPOA-annotated
MONDO within **2 is-a hops** up or down (so a grouping is reconciled with its
near subtypes, not its entire category). The ontology root and other non-disease
groupings are excluded. Obsolete MONDO terms are resolved to their replacements
(e.g. HPOA's Dravet maps to an obsoleted term that resolves to the live
`MONDO:0100135`, becoming an exact match). **Limitation:** lineage catches
ancestor/descendant relationships, not siblings; and broad dismech groupings (e.g.
spinal muscular atrophy) still aggregate many subtypes — see the breadth column.

</div>

## Lineage-shared — dismech grouping ↔ HPOA subtypes

dismech diseases reconciled to HPOA annotations on near MONDO relatives. **nodes**
= how many HPOA-annotated MONDO terms were rolled up (high = a broad grouping;
read those closure-F1s with care, since they compare a grouping against unioned
subtypes).

```js
const lineage = dc.lineage_shared.map((r) => ({
  disease: r.label, mondo: r.mondo, match: r.match_type, nodes: r.n_hpoa_nodes, closureF1: r.closure_f1,
}));
const lineageSearch = view(Inputs.search(lineage, {placeholder: "search lineage-shared…"}));
```

```js
Inputs.table(lineageSearch, {
  sort: "nodes",
  reverse: true,
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
    closureF1: (x) => x.toFixed(2),
  },
  width: {disease: 280},
})
```

## Where dismech extends HPOA

dismech-curated MONDO diseases with no HPOA annotations within 2 hops.
**direct xref = no** means the MONDO has no OMIM/ORPHA exact-match at all (genuinely
beyond HPOA's rare-disease scope, e.g. common/acquired disease).

```js
const dismechOnly = dc.dismech_only.map((r) => ({
  disease: r.label, mondo: r.mondo, phenotypes: r.n_terms, directXref: r.beyond_omim_orpha ? "no" : "yes",
}));
const onlySearch = view(Inputs.search(dismechOnly, {placeholder: "search dismech-only…"}));
```

```js
Inputs.table(onlySearch, {
  sort: "phenotypes",
  reverse: true,
  format: {mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`},
  width: {disease: 300},
})
```

## Diseases unique to HPOA

MONDO diseases HPOA characterizes that dismech doesn't (and that aren't within 2 hops
of a dismech disease), ranked by HPOA annotation richness. This reflects the
resources' different scope — HPOA is exhaustive across rare disease — and can guide
curation prioritisation; it isn't a deficiency in dismech.

```js
const gaps = dc.hpoa_only.map((r) => ({
  disease: r.label, mondo: r.mondo, phenotypes: r.n_terms, sources: r.hpoa_ids.join(", "),
}));
const gapSearch = view(Inputs.search(gaps, {placeholder: "search coverage gaps…"}));
```

```js
Inputs.table(gapSearch, {
  sort: "phenotypes",
  reverse: true,
  format: {mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`},
  width: {disease: 300},
})
```
