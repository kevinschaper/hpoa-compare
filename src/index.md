# Overview

How well does dismech's curated phenotype export agree with HPO's gold-standard
`phenotype.hpoa`? This compares the two **hierarchy-aware** — crediting agreement
anywhere along an is-a lineage, not just on identical term IDs — after reconciling
the disease axis through MONDO SSSOM (`skos:exactMatch` → OMIM/ORPHA/DECIPHER,
unioned).

```js
const coverage = await FileAttachment("data/coverage.json").json();
const aggregates = await FileAttachment("data/aggregates.json").json();
const perDisease = await FileAttachment("data/per_disease.json").json();
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Comparable diseases</h2>
    <span class="big">${coverage.comparable.toLocaleString()}</span>
    shared MONDO; ${coverage.dismech_only} dismech-only (<a href="./coverage">coverage →</a>)
  </div>
  <div class="card">
    <h2>Term comparability</h2>
    <span class="big">${(coverage.term_comparability * 100).toFixed(0)}%</span>
    of dismech rows are HP-typed (rest are <code>DISMECH:</code> synthetics)
  </div>
  <div class="card">
    <h2>Closure micro-F1</h2>
    <span class="big">${aggregates.closure.micro.f1.toFixed(3)}</span>
    vs exact ${aggregates.exact.micro.f1.toFixed(3)}
  </div>
  <div class="card">
    <h2>Specificity tilt</h2>
    <span class="big">${aggregates.more_specific}/${aggregates.more_general}</span>
    dismech terms finer / coarser than HPOA
  </div>
</div>

## Exact vs. hierarchy-aware agreement

Exact-ID matching undercounts agreement: dismech and HPOA often annotate the same
lineage at different depths. Ancestor-closure scoring credits those near-misses —
the gap between the two bars is the agreement that exact matching misses.

```js
const aggRows = ["precision", "recall", "f1"].flatMap((k) => [
  {metric: k, method: "exact", value: aggregates.exact.micro[k]},
  {metric: k, method: "closure", value: aggregates.closure.micro[k]},
]);
```

```js
Plot.plot({
  x: {label: null, domain: ["exact", "closure"]},
  fx: {label: null},
  y: {label: "micro-average", domain: [0, 1], grid: true},
  color: {legend: true, domain: ["exact", "closure"], range: ["#9aa7b4", "#4269d0"]},
  marks: [
    Plot.barY(aggRows, {fx: "metric", x: "method", y: "value", fill: "method"}),
    Plot.text(aggRows, {fx: "metric", x: "method", y: "value", text: (d) => d.value.toFixed(2), dy: -6}),
    Plot.ruleY([0]),
  ],
})
```

## Per-disease lift

Each point is a disease: exact F1 (x) vs closure F1 (y). Points above the diagonal
are diseases where hierarchy awareness recovered agreement that exact matching lost.

```js
Plot.plot({
  grid: true,
  width,
  aspectRatio: 1,
  x: {label: "exact F1", domain: [0, 1]},
  y: {label: "closure F1", domain: [0, 1]},
  marks: [
    Plot.line([[0, 0], [1, 1]], {stroke: "currentColor", strokeOpacity: 0.3, strokeDasharray: "4"}),
    Plot.dot(perDisease, {
      x: (d) => d.exact.f1,
      y: (d) => d.closure.f1,
      r: 3,
      fill: "#4269d0",
      fillOpacity: 0.5,
      channels: {disease: (d) => d.label, dismech: "n_dismech", hpoa: "n_hpoa"},
      tip: true,
    }),
  ],
})
```

## Distribution of agreement

```js
Plot.plot({
  width,
  x: {label: "closure F1", domain: [0, 1]},
  y: {label: "diseases", grid: true},
  marks: [
    Plot.rectY(perDisease, Plot.binX({y: "count"}, {x: (d) => d.closure.f1, thresholds: 20, fill: "#4269d0"})),
    Plot.ruleY([0]),
  ],
})
```

The [per-disease table](./diseases) ranks every comparison; [novel & missing](./diff)
lists the actionable term-level differences. See [methods](./methods) for exactly
what is and isn't compared.
