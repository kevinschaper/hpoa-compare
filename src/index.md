# Overview

dismech and HPO's `phenotype.hpoa` are **two independently-built disease–phenotype
resources** with different scope and method. HPOA is the broad, established HPO
annotation set — exhaustive per disease, derived from literature, registries and
Orphanet, organized around OMIM/Orphanet. dismech is a newer, mechanism-driven,
MONDO-centric knowledge base — selective, focused on disease mechanism, and
extending to common and acquired disease beyond HPOA's rare-disease scope.

This compares them **as peers**: where they *overlap*, and what each holds
*uniquely*. Neither is treated as ground truth — a difference is a difference in
approach, not an error. Comparison is hierarchy-aware (crediting agreement anywhere
along the HPO is-a lineage) after reconciling the disease axis through MONDO.

```js
const coverage = await FileAttachment("data/coverage.json").json();
const aggregates = await FileAttachment("data/aggregates.json").json();
const perDisease = await FileAttachment("data/per_disease.json").json();
const scored = perDisease.filter((d) => d.match_type === "exact");
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Diseases compared</h2>
    <span class="big">${coverage.exact_shared.toLocaleString()}</span>
    shared MONDO; +${coverage.lineage_shared} via lineage (<a href="./coverage">coverage →</a>)
  </div>
  <div class="card">
    <h2>Phenotype overlap</h2>
    <span class="big">${aggregates.closure.micro.jaccard.toFixed(2)}</span>
    Jaccard, hierarchy-aware (exact-ID ${aggregates.exact.micro.jaccard.toFixed(2)})
  </div>
  <div class="card">
    <h2>of dismech, shared</h2>
    <span class="big">${(aggregates.closure.micro.dismech_in_hpoa * 100).toFixed(0)}%</span>
    of dismech's phenotypes are also in HPOA
  </div>
  <div class="card">
    <h2>of HPOA, shared</h2>
    <span class="big">${(aggregates.closure.micro.hpoa_in_dismech * 100).toFixed(0)}%</span>
    of HPOA's phenotypes are also in dismech
  </div>
</div>

The two directional shares are deliberately asymmetric — dismech's curated set sits
largely *within* HPOA's broader one, while HPOA holds much that dismech doesn't (yet)
cover. That is the expected signature of a selective resource beside an exhaustive
one, not a deficiency in either.

## Overlap, exact-ID vs hierarchy-aware

Matching identical HP IDs understates overlap, because the two resources often
annotate the same lineage at different depths. Crediting agreement along the is-a
hierarchy recovers it — the lift between the two bars is overlap that exact-ID
matching misses.

```js
const dims = [
  {k: "overlap (Jaccard)", ex: aggregates.exact.micro.jaccard, cl: aggregates.closure.micro.jaccard},
  {k: "of dismech, shared", ex: aggregates.exact.micro.dismech_in_hpoa, cl: aggregates.closure.micro.dismech_in_hpoa},
  {k: "of HPOA, shared", ex: aggregates.exact.micro.hpoa_in_dismech, cl: aggregates.closure.micro.hpoa_in_dismech},
];
const aggRows = dims.flatMap((d) => [
  {metric: d.k, method: "exact-ID", value: d.ex},
  {metric: d.k, method: "hierarchy-aware", value: d.cl},
]);
```

```js
Plot.plot({
  width,
  marginLeft: 60,
  x: {label: null, domain: ["exact-ID", "hierarchy-aware"]},
  fx: {label: null},
  y: {label: "micro-average", domain: [0, 1], grid: true},
  color: {legend: true, domain: ["exact-ID", "hierarchy-aware"], range: ["#9aa7b4", "#4269d0"]},
  marks: [
    Plot.barY(aggRows, {fx: "metric", x: "method", y: "value", fill: "method"}),
    Plot.text(aggRows, {fx: "metric", x: "method", y: "value", text: (d) => d.value.toFixed(2), dy: -6}),
    Plot.ruleY([0]),
  ],
})
```

## Per-disease overlap

Each point is a disease: exact-ID overlap (x) vs hierarchy-aware overlap (y), both
Jaccard. Points above the diagonal are diseases where hierarchy awareness recovered
shared content that exact-ID matching missed.

```js
Plot.plot({
  grid: true,
  width,
  aspectRatio: 1,
  x: {label: "exact-ID overlap (Jaccard)", domain: [0, 1]},
  y: {label: "hierarchy-aware overlap (Jaccard)", domain: [0, 1]},
  marks: [
    Plot.line([[0, 0], [1, 1]], {stroke: "currentColor", strokeOpacity: 0.3, strokeDasharray: "4"}),
    Plot.dot(scored, {
      x: (d) => d.exact.jaccard,
      y: (d) => d.closure.jaccard,
      r: 3,
      fill: "#4269d0",
      fillOpacity: 0.5,
      channels: {disease: (d) => d.label, dismech: "n_dismech", hpoa: "n_hpoa"},
      tip: true,
    }),
  ],
})
```

## Distribution of overlap

```js
Plot.plot({
  width,
  x: {label: "hierarchy-aware overlap (Jaccard)", domain: [0, 1]},
  y: {label: "diseases", grid: true},
  marks: [
    Plot.rectY(scored, Plot.binX({y: "count"}, {x: (d) => d.closure.jaccard, thresholds: 20, fill: "#4269d0"})),
    Plot.ruleY([0]),
  ],
})
```

Browse individual diseases on the [per-disease](./diseases) page; see what each
resource holds uniquely on [novel & missing](./diff); see [methods](./methods) for
the framing and exactly what is and isn't compared.
