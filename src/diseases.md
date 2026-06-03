# Per-disease

Every comparable disease (a dismech MONDO entry whose `skos:exactMatch` resolves
to ≥1 disease present in HPOA), ranked. Sort any column; search by name or MONDO ID.

```js
const perDisease = await FileAttachment("data/per_disease.json").json();
```

```js
const rows = perDisease.map((d) => ({
  disease: d.label,
  mondo: d.mondo,
  dismech: d.n_dismech,
  hpoa: d.n_hpoa,
  exactF1: d.exact.f1,
  closureF1: d.closure.f1,
  resnik: d.resnik_bma,
  novel: d.n_novel,
  missing: d.n_missing,
  finer: d.more_specific,
  coarser: d.more_general,
}));
```

```js
const search = view(Inputs.search(rows, {placeholder: "search disease or MONDO…"}));
```

```js
Inputs.table(search, {
  sort: "closureF1",
  reverse: true,
  columns: ["disease", "mondo", "dismech", "hpoa", "exactF1", "closureF1", "resnik", "novel", "missing", "finer", "coarser"],
  header: {
    dismech: "dismech terms",
    hpoa: "HPOA terms",
    exactF1: "exact F1",
    closureF1: "closure F1",
    resnik: "Resnik BMA",
    finer: "↓ finer",
    coarser: "↑ coarser",
  },
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
    exactF1: (x) => x.toFixed(2),
    closureF1: (x) => x.toFixed(2),
    resnik: (x) => x.toFixed(2),
  },
  width: {disease: 260},
})
```
