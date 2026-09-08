---
sql:
  history: data/history.parquet
---

# Over time

How the two resources — and their overlap — have changed **release by release**.
One snapshot is a dismech release tag paired with the newest HPO release available
on that date; the MONDO and HPO graphs are held at their current release for every
snapshot, so the trends reflect annotation change rather than ontology drift.

```js
const releases = await FileAttachment("data/history_releases.json").json();
for (const r of releases) r.date = new Date(r.release_date);
const latest = releases.at(-1);
const first = releases[0];
const DISMECH = "#4269d0", HPOA = "#ff725c", SHARED = "#3ca951", MUTED = "#9aa7b4";
// dates where the paired HPO release changed (drawn as rules)
const hpoSteps = releases.filter((r, i) => i > 0 && r.hpoa_release !== releases[i - 1].hpoa_release);
const hpoRules = () => [
  Plot.ruleX(hpoSteps, {x: "date", stroke: HPOA, strokeOpacity: 0.35, strokeDasharray: "3,3"}),
  Plot.text(hpoSteps, {x: "date", y: 0, text: (d) => `HPOA ${d.hpoa_release}`, fill: HPOA, fontSize: 9, rotate: -90, textAnchor: "start", dx: -4, dy: -4}),
];
const tipX = {x: "date", channels: {release: "release", HPOA: "hpoa_release"}};
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Releases</h2>
    <span class="big">${releases.length}</span>
    ${first.release} (${first.release_date}) → ${latest.release} (${latest.release_date})
  </div>
  <div class="card">
    <h2>dismech diseases</h2>
    <span class="big">${latest.dismech_diseases.toLocaleString()}</span>
    from ${first.dismech_diseases.toLocaleString()} in ${first.release}
  </div>
  <div class="card">
    <h2>Shared diseases</h2>
    <span class="big">${latest.exact_shared.toLocaleString()}</span>
    exact MONDO matches, from ${first.exact_shared.toLocaleString()}
  </div>
  <div class="card">
    <h2>Phenotype overlap</h2>
    <span class="big">${latest.closure_micro_jaccard.toFixed(2)}</span>
    hierarchy-aware Jaccard, from ${first.closure_micro_jaccard.toFixed(2)}
  </div>
</div>

## Diseases in each set

dismech's disease count by how each disease relates to HPOA: an **exact** MONDO
match, a **lineage** match (grouping ↔ subtype within 2 hops), or **dismech-only**.
HPOA's own disease count (MONDO space) is on the right — a different scale, so its
own chart.

```js
const diseaseRows = releases.flatMap((r) => [
  {date: r.date, release: r.release, set: "exact-shared", n: r.exact_shared},
  {date: r.date, release: r.release, set: "lineage-shared", n: r.lineage_shared},
  {date: r.date, release: r.release, set: "dismech-only", n: r.dismech_only},
]);
const SET_COLORS = {"exact-shared": "#4269d0", "lineage-shared": "#3ca951", "dismech-only": "#a463f2"};
```

<div class="grid grid-cols-2">
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 300, marginLeft: 50,
      title: "dismech diseases, by relation to HPOA",
      x: {label: null},
      y: {label: "diseases", grid: true},
      color: {legend: true, domain: Object.keys(SET_COLORS), range: Object.values(SET_COLORS)},
      marks: [
        Plot.areaY(diseaseRows, {x: "date", y: "n", fill: "set", order: Object.keys(SET_COLORS), fillOpacity: 0.85}),
        Plot.ruleY([0]),
        Plot.tip(diseaseRows, Plot.pointerX(Plot.stackY({x: "date", y: "n", fill: "set", order: Object.keys(SET_COLORS), channels: {release: "release"}}))),
      ],
    }))}
  </div>
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 300, marginLeft: 50,
      title: "HPOA diseases (lifted to MONDO)",
      x: {label: null},
      y: {label: "diseases", grid: true, zero: true},
      marks: [
        ...hpoRules(),
        Plot.lineY(releases, {x: "date", y: "hpoa_diseases_mondo", stroke: HPOA, strokeWidth: 2, curve: "step-after"}),
        Plot.dot(releases, {x: "date", y: "hpoa_diseases_mondo", fill: HPOA, r: 2.5}),
        Plot.tip(releases, Plot.pointerX({...tipX, y: "hpoa_diseases_mondo"})),
        Plot.ruleY([0]),
      ],
    }))}
  </div>
</div>

## Annotations in each set

Distinct (disease, phenotype) pairs on each side, counted in MONDO space over
positive `aspect = P` HP-typed rows. HPOA's total is an order of magnitude larger,
so again the two are drawn separately.

<div class="grid grid-cols-2">
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 260, marginLeft: 55,
      title: "dismech disease–phenotype pairs",
      x: {label: null}, y: {label: "pairs", grid: true, zero: true},
      marks: [
        Plot.areaY(releases, {x: "date", y: "dismech_phenotype_pairs", fill: DISMECH, fillOpacity: 0.15}),
        Plot.lineY(releases, {x: "date", y: "dismech_phenotype_pairs", stroke: DISMECH, strokeWidth: 2}),
        Plot.tip(releases, Plot.pointerX({...tipX, y: "dismech_phenotype_pairs"})),
        Plot.ruleY([0]),
      ],
    }))}
  </div>
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 260, marginLeft: 55,
      title: "HPOA disease–phenotype pairs",
      x: {label: null}, y: {label: "pairs", grid: true, zero: true},
      marks: [
        ...hpoRules(),
        Plot.lineY(releases, {x: "date", y: "hpoa_phenotype_pairs_mondo", stroke: HPOA, strokeWidth: 2, curve: "step-after"}),
        Plot.dot(releases, {x: "date", y: "hpoa_phenotype_pairs_mondo", fill: HPOA, r: 2.5}),
        Plot.tip(releases, Plot.pointerX({...tipX, y: "hpoa_phenotype_pairs_mondo"})),
        Plot.ruleY([0]),
      ],
    }))}
  </div>
</div>

## Overlap on shared diseases

Hierarchy-aware phenotype overlap, micro-averaged over exact MONDO matches. The
three lines are the same measures as on the [overview](./): order-free Jaccard and
the two directional shares. As dismech grows into diseases HPOA covers exhaustively,
expect *of HPOA ⊂ dismech* to move slowly and *of dismech ⊂ HPOA* to stay high.

```js
const overlapRows = releases.flatMap((r) => [
  {date: r.date, release: r.release, metric: "of dismech ⊂ HPOA", value: r.closure_micro_dismech_in_hpoa},
  {date: r.date, release: r.release, metric: "overlap (Jaccard)", value: r.closure_micro_jaccard},
  {date: r.date, release: r.release, metric: "of HPOA ⊂ dismech", value: r.closure_micro_hpoa_in_dismech},
]);
const METRIC_COLORS = {"of dismech ⊂ HPOA": "#4269d0", "overlap (Jaccard)": "#3ca951", "of HPOA ⊂ dismech": "#ff725c"};
// Jaccard always sits at or below the smaller directional share, so nudge its end label
// down and that share's up (data units); keeps the labels apart where the lines converge.
const END_DY = {"of dismech ⊂ HPOA": 0, "overlap (Jaccard)": -0.025, "of HPOA ⊂ dismech": 0.025};
```

```js
Plot.plot({
  width, height: 320, marginLeft: 45, marginRight: 130,
  x: {label: null},
  y: {label: "micro-average (hierarchy-aware)", domain: [0, 1], grid: true},
  color: {legend: true, domain: Object.keys(METRIC_COLORS), range: Object.values(METRIC_COLORS)},
  marks: [
    ...hpoRules(),
    Plot.lineY(overlapRows, {x: "date", y: "value", stroke: "metric", strokeWidth: 2}),
    Plot.text(overlapRows, Plot.selectLast({x: "date", y: (d) => d.value + END_DY[d.metric], z: "metric", text: (d) => `${d.metric} ${d.value.toFixed(2)}`, textAnchor: "start", dx: 6, fill: "currentColor", fontSize: 10})),
    Plot.tip(overlapRows, Plot.pointerX({x: "date", y: "value", channels: {metric: "metric", release: "release"}})),
    Plot.ruleY([0]),
  ],
})
```

## Where the growth went

Diseases entering dismech per release (first release in which a MONDO appears),
split by whether HPOA already covered that disease. Computed in the browser with
DuckDB over the per-disease history.

```sql id=newPerRelease
WITH firsts AS (
  SELECT mondo, min(release_date) AS first_date
  FROM history GROUP BY mondo
), joined AS (
  SELECT h.release, h.release_date, h.match_type
  FROM history h JOIN firsts f ON h.mondo = f.mondo AND h.release_date = f.first_date
)
SELECT release, release_date,
       CASE WHEN match_type = 'exact' THEN 'exact-shared'
            WHEN match_type = 'dismech-only' THEN 'dismech-only'
            ELSE 'lineage-shared' END AS relation,
       count(*) AS n
FROM joined
GROUP BY ALL ORDER BY release_date, relation
```

```js
const newRows = newPerRelease.toArray().map((d) => ({...d, date: new Date(d.release_date), n: Number(d.n)}));
```

```js
Plot.plot({
  width, height: 280, marginLeft: 45,
  x: {label: null, interval: "week"},
  y: {label: "diseases first seen", grid: true},
  color: {legend: true, domain: Object.keys(SET_COLORS), range: Object.values(SET_COLORS)},
  marks: [
    Plot.rectY(newRows, {x: "date", y: "n", fill: "relation", order: Object.keys(SET_COLORS), inset: 0.5, tip: true, channels: {release: "release"}}),
    Plot.ruleY([0]),
  ],
})
```

## One disease over time

Pick a dismech disease to see its phenotype counts and overlap across releases.
Diseases that have been in dismech longest have the most history; a flat line
means the release changed nothing for that disease.

```sql id=diseaseIndex
SELECT mondo, any_value(label ORDER BY release_date DESC) AS label,
       count(*) AS n_releases, min(release_date) AS since,
       any_value(match_type ORDER BY release_date DESC) AS match_type,
       any_value(n_dismech ORDER BY release_date DESC) AS n_dismech
FROM history GROUP BY mondo ORDER BY label
```

```js
const diseaseList = diseaseIndex.toArray().map((d) => ({...d}));
const byMondo = new Map(diseaseList.map((d) => [d.mondo, d]));
const pick = view(Inputs.select(diseaseList, {
  label: "disease",
  format: (d) => `${d.label} (${d.mondo}) · ${d.match_type} · since ${d.since}`,
  value: diseaseList.find((d) => d.mondo === "MONDO:0100135") ?? diseaseList[0],
  width: 520,
}));
```

```sql id=diseaseHistory
SELECT release, release_date, hpoa_release, match_type,
       n_dismech, n_hpoa, n_shared, n_novel, n_missing,
       closure_jaccard, closure_dismech_in_hpoa, closure_hpoa_in_dismech, exact_jaccard, resnik_bma
FROM history WHERE mondo = ${pick.mondo} ORDER BY release_date
```

```js
const dh = diseaseHistory.toArray().map((d) => ({...d, date: new Date(d.release_date)}));
const countRows = dh.flatMap((d) => [
  {date: d.date, release: d.release, series: "dismech", n: Number(d.n_dismech)},
  {date: d.date, release: d.release, series: "HPOA", n: Number(d.n_hpoa)},
  {date: d.date, release: d.release, series: "in common", n: Number(d.n_shared)},
]);
const COUNT_COLORS = {dismech: DISMECH, HPOA: HPOA, "in common": SHARED};
const shareRows = dh.flatMap((d) => [
  {date: d.date, release: d.release, metric: "of dismech ⊂ HPOA", value: d.closure_dismech_in_hpoa},
  {date: d.date, release: d.release, metric: "overlap (Jaccard)", value: d.closure_jaccard},
  {date: d.date, release: d.release, metric: "of HPOA ⊂ dismech", value: d.closure_hpoa_in_dismech},
]);
```

<div class="grid grid-cols-2">
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 260, marginLeft: 40, marginRight: 20,
      title: `${pick.label} — phenotypes`,
      caption: `latest (${dh.at(-1)?.release}): dismech ${dh.at(-1)?.n_dismech} · HPOA ${dh.at(-1)?.n_hpoa} · in common ${dh.at(-1)?.n_shared}`,
      x: {label: null}, y: {label: "phenotypes", grid: true, zero: true},
      color: {legend: true, domain: Object.keys(COUNT_COLORS), range: Object.values(COUNT_COLORS)},
      marks: [
        Plot.lineY(countRows, {x: "date", y: "n", stroke: "series", strokeWidth: 2, curve: "step-after"}),
        Plot.dot(countRows, {x: "date", y: "n", fill: "series", r: 2.5}),
        Plot.tip(countRows, Plot.pointerX({x: "date", y: "n", channels: {series: "series", release: "release"}})),
        Plot.ruleY([0]),
      ],
    }))}
  </div>
  <div class="card">
    ${resize((width) => Plot.plot({
      width, height: 260, marginLeft: 40, marginRight: 20,
      title: `${pick.label} — hierarchy-aware overlap`,
      caption: `latest: of dismech ⊂ HPOA ${dh.at(-1)?.closure_dismech_in_hpoa.toFixed(2)} · overlap ${dh.at(-1)?.closure_jaccard.toFixed(2)} · of HPOA ⊂ dismech ${dh.at(-1)?.closure_hpoa_in_dismech.toFixed(2)}`,
      x: {label: null}, y: {label: null, domain: [0, 1], grid: true},
      color: {legend: true, domain: Object.keys(METRIC_COLORS), range: Object.values(METRIC_COLORS)},
      marks: [
        Plot.lineY(shareRows, {x: "date", y: "value", stroke: "metric", strokeWidth: 2, curve: "step-after"}),
        Plot.dot(shareRows, {x: "date", y: "value", fill: "metric", r: 2.5}),
        Plot.tip(shareRows, Plot.pointerX({x: "date", y: "value", channels: {metric: "metric", release: "release"}})),
        Plot.ruleY([0]),
      ],
    }))}
  </div>
</div>

```js
Inputs.table(dh, {
  columns: ["release", "release_date", "hpoa_release", "match_type", "n_dismech", "n_hpoa", "n_shared", "n_novel", "n_missing", "closure_jaccard", "exact_jaccard", "resnik_bma"],
  header: {release_date: "date", hpoa_release: "HPOA", match_type: "match", n_dismech: "dismech", n_hpoa: "HPOA phen.", n_shared: "in common", n_novel: "dismech-only", n_missing: "HPOA-only", closure_jaccard: "overlap", exact_jaccard: "exact overlap", resnik_bma: "Resnik"},
  format: {closure_jaccard: (v) => v.toFixed(2), exact_jaccard: (v) => v.toFixed(2), resnik_bma: (v) => v.toFixed(2)},
  rows: 12, select: false,
})
```

## Biggest movers, last release

Diseases whose phenotype set changed most between the two most recent dismech
releases (by change in dismech phenotype count), with the effect on overlap.

```sql id=movers
WITH ranked AS (
  SELECT release, dense_rank() OVER (ORDER BY release_date DESC, release DESC) AS rk
  FROM (SELECT DISTINCT release, release_date FROM history)
), cur AS (SELECT * FROM history WHERE release = (SELECT release FROM ranked WHERE rk = 1)),
   prev AS (SELECT * FROM history WHERE release = (SELECT release FROM ranked WHERE rk = 2))
SELECT c.mondo, c.label, c.match_type,
       p.n_dismech AS before, c.n_dismech AS after, c.n_dismech - p.n_dismech AS delta,
       p.closure_jaccard AS overlap_before, c.closure_jaccard AS overlap_after
FROM cur c JOIN prev p USING (mondo)
WHERE c.n_dismech <> p.n_dismech
ORDER BY abs(c.n_dismech - p.n_dismech) DESC, c.mondo
LIMIT 25
```

```js
const moverRows = movers.toArray().map((d) => ({...d}));
display(moverRows.length
  ? Inputs.table(moverRows, {
      columns: ["label", "mondo", "before", "after", "delta", "overlap_before", "overlap_after"],
      header: {label: "disease", before: "before", after: "after", delta: "Δ phen.", overlap_before: "overlap before", overlap_after: "overlap after"},
      format: {overlap_before: (v) => v.toFixed(2), overlap_after: (v) => v.toFixed(2)},
      width: {label: 230, mondo: 110, before: 50, after: 50, delta: 55},
      rows: 25, select: false,
    })
  : html`<div class="muted">No disease's phenotype set changed between ${releases.at(-2)?.release} and ${latest.release}.</div>`);
```

<div class="small note">

Per-release results are cached in the repository (`data/history/<tag>.parquet`),
so a refresh only computes the newest release. The per-disease table shipped to
the browser is `data/history.parquet`, queried here with DuckDB-Wasm. See
[methods](./methods#release-history) for how snapshots are paired.

</div>
