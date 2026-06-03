# Per-disease

Every comparable disease (a dismech MONDO whose match resolves to ≥1 HPOA-annotated
MONDO). Two views: the **landscape** places all diseases by precision and recall at
once; the **focus list** below shows individual diseases as bars you can rank and search.

```js
const perDisease = await FileAttachment("data/per_disease.json").json();
const labelOf = new Map(perDisease.map((d) => [d.mondo, d.label]));
const trunc = (s, n = 34) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const MATCH = ["exact", "descendant", "ancestor", "mixed"];
const MATCH_COLORS = ["#4269d0", "#3ca951", "#efb118", "#ff725c"];
```

## Agreement landscape

Each dot is a disease: **closure recall** (how much of HPOA's profile dismech covers)
against **closure precision** (how much of dismech's is in HPOA). Size = number of
HPOA terms; color = how the disease matched on the MONDO graph. High-precision /
low-recall (lower-right) is the expected dismech signature — curated-selective, not
exhaustive. Hover any point for detail.

```js
Plot.plot({
  width,
  height: Math.min(560, width),
  marginRight: 80,
  grid: true,
  x: {label: "closure recall →", domain: [0, 1], percent: true},
  y: {label: "↑ closure precision", domain: [0, 1], percent: true},
  r: {range: [2, 14]},
  color: {legend: true, domain: MATCH, range: MATCH_COLORS},
  marks: [
    Plot.dot(perDisease, {
      x: (d) => d.closure.recall,
      y: (d) => d.closure.precision,
      r: "n_hpoa",
      fill: "match_type",
      fillOpacity: 0.45,
      stroke: "match_type",
      channels: {
        disease: (d) => d.label,
        "exact F1": (d) => d.exact.f1,
        "closure F1": (d) => d.closure.f1,
        "dismech / HPOA terms": (d) => `${d.n_dismech} / ${d.n_hpoa}`,
      },
      tip: true,
    }),
  ],
})
```

## Focus list

Search for a disease, or pick a lens — the 40 most extreme diseases on that
dimension. Each disease is a track from its **exact F1** (○) to its **closure F1**
(●); the segment length is the lift from hierarchy-aware scoring.

```js
const query = view(Inputs.text({placeholder: "filter by disease or MONDO…", width: 280}));
const lens = view(
  Inputs.select(
    new Map([
      ["weakest closure F1", (a, b) => a.closure.f1 - b.closure.f1],
      ["strongest closure F1", (a, b) => b.closure.f1 - a.closure.f1],
      ["biggest hierarchy lift", (a, b) => (b.closure.f1 - b.exact.f1) - (a.closure.f1 - a.exact.f1)],
      ["most novel (dismech-only)", (a, b) => b.n_novel - a.n_novel],
      ["most missing (HPOA-only)", (a, b) => b.n_missing - a.n_missing],
    ]),
    {label: "focus", value: (a, b) => a.closure.f1 - b.closure.f1},
  ),
);
```

```js
const q = (query || "").toLowerCase().trim();
const matched = perDisease.filter(
  (d) => !q || d.label.toLowerCase().includes(q) || d.mondo.toLowerCase().includes(q),
);
const focus = matched.slice().sort(lens).slice(0, 40);
const order = focus.map((d) => d.mondo);
```

```js
Plot.plot({
  width,
  height: focus.length * 22 + 46,
  marginLeft: 250,
  marginRight: 90,
  x: {domain: [0, 1], grid: true, label: "F1: exact ○ → closure ●", percent: true},
  y: {domain: order, label: null, tickFormat: (m) => trunc(labelOf.get(m) ?? m)},
  color: {domain: MATCH, range: MATCH_COLORS},
  marks: [
    Plot.ruleY(focus, {y: "mondo", x1: (d) => d.exact.f1, x2: (d) => d.closure.f1, stroke: "#bcc6d0", strokeWidth: 2}),
    Plot.dot(focus, {y: "mondo", x: (d) => d.exact.f1, r: 3.5, fill: "var(--theme-background)", stroke: "#9aa7b4"}),
    Plot.dot(focus, {
      y: "mondo",
      x: (d) => d.closure.f1,
      r: 5,
      fill: "match_type",
      channels: {
        disease: (d) => d.label,
        recall: (d) => d.closure.recall,
        precision: (d) => d.closure.precision,
        novel: "n_novel",
        missing: "n_missing",
        match: "match_type",
      },
      tip: true,
    }),
    Plot.text(focus, {
      y: "mondo",
      x: (d) => d.closure.f1,
      text: (d) => (d.n_novel || d.n_missing ? `+${d.n_novel} / −${d.n_missing}` : ""),
      dx: 12,
      textAnchor: "start",
      fill: "currentColor",
      fillOpacity: 0.55,
      fontSize: 10,
    }),
  ],
})
```

<div class="small note">

Showing ${focus.length} of ${matched.length} matched diseases. ○ exact-ID F1, ● ancestor-closure F1; the `+novel / −missing` text counts term-level differences (see [novel & missing](./diff)). Lineage (non-exact) matches aggregate subtype annotations, so their recall reads low by construction.

</div>
