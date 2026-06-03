# Frequency

When **both** resources assert the same phenotype for the same disease, do they
agree on *how often* it occurs? Each side's frequency — an HP frequency term, a
percentage, or an `n/m` ratio — is flattened to one of the six HP **frequency
bands**, and the bands are compared. Restricted to phenotypes **in common** on
**exact disease matches**.

```js
const fr = await FileAttachment("data/frequency.json").json();
const s = fr.summary;
const both = s.both_specified;
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Same band</h2>
    <span class="big">${(100 * s.same / both).toFixed(0)}%</span>
    ${s.same.toLocaleString()} of ${both.toLocaleString()} shared phenotypes
  </div>
  <div class="card">
    <h2>Adjacent band</h2>
    <span class="big">${(100 * s.adjacent / both).toFixed(0)}%</span>
    off by one band
  </div>
  <div class="card">
    <h2>Disagree</h2>
    <span class="big">${(100 * s.disagree / both).toFixed(0)}%</span>
    ≥2 bands apart
  </div>
  <div class="card">
    <h2>One side only</h2>
    <span class="big">${s.one_side_only.toLocaleString()}</span>
    only one resource gives a frequency
  </div>
</div>

```js
const dist = [
  {band: "same", n: s.same},
  {band: "adjacent", n: s.adjacent},
  {band: "disagree", n: s.disagree},
];
```

```js
Plot.plot({
  width,
  height: 90,
  marginLeft: 10,
  x: {label: "shared phenotypes (both specify a frequency)", percent: false},
  color: {legend: true, domain: ["same", "adjacent", "disagree"], range: ["#3ca951", "#efb118", "#e15759"]},
  marks: [
    Plot.barX(dist, {x: "n", fill: "band", order: ["same", "adjacent", "disagree"]}),
    Plot.text(dist, Plot.stackX({x: "n", text: (d) => d.n.toLocaleString(), fill: "white"})),
  ],
})
```

Concordance is high — most shared phenotypes land in the same or an adjacent band.
The bands run **Obligate → Very frequent → Frequent → Occasional → Very rare →
Excluded**; "adjacent" is one step on that scale.

## Where they disagree (≥2 bands)

```js
const rows = fr.disagreements.map((r) => ({
  disease: r.disease, mondo: r.mondo, phenotype: r.label, hp: r.phenotype,
  dismech: r.dismech, hpoa: r.hpoa, apart: r.distance,
}));
const search = view(Inputs.search(rows, {placeholder: "search disease or phenotype…"}));
```

```js
Inputs.table(search, {
  sort: "apart",
  reverse: true,
  columns: ["disease", "mondo", "phenotype", "dismech", "hpoa", "apart"],
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
  },
  width: {disease: 240, phenotype: 220},
})
```

<div class="small note">

**Caveats.** Small-cohort ratios inflate the extremes — HPOA `1/1` maps to
*Obligate* (100%) on n=1, so a dismech *Occasional* vs HPOA *Obligate* may reflect
cohort size, not real disagreement. *Excluded* vs a present band is a genuine
present-vs-absent conflict and worth a look. Frequencies are not yet compared on
**lineage** disease matches (the HPOA side aggregates subtypes there).

</div>
