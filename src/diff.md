# Novel & missing

These are **disease–phenotype associations** — each row is one *(disease,
phenotype)* pair, the unit HPOA annotates. **Novel** = dismech asserts a phenotype
for a disease where HPOA has no ancestor or descendant of it (a candidate new
association, or a curation error to check). **Missing** = HPOA asserts it and
dismech has no ancestor/descendant (a recall gap).

The same **phenotype** (HP term) recurs across many diseases, so the totals below
count *associations*, not distinct phenotypes — both numbers are shown so the
difference is explicit. Ranked by phenotype **depth** (longest is-a path from
*Phenotypic abnormality*; deeper = more specific); ≤25 associations per disease.

```js
const perDisease = await FileAttachment("data/per_disease.json").json();
```

```js
const novel = perDisease.flatMap((d) =>
  d.novel_terms.map((t) => ({disease: d.label, mondo: d.mondo, phenotype: t.id, label: t.label, depth: t.depth})),
);
const missing = perDisease.flatMap((d) =>
  d.missing_terms.map((t) => ({disease: d.label, mondo: d.mondo, phenotype: t.id, label: t.label, depth: t.depth})),
);
const uniq = (rows, k) => new Set(rows.map((r) => r[k])).size;
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Novel — dismech only</h2>
    <span class="big">${novel.length.toLocaleString()}</span> associations
    <div class="small muted">${uniq(novel, "phenotype").toLocaleString()} distinct phenotypes · ${uniq(novel, "mondo").toLocaleString()} diseases</div>
  </div>
  <div class="card">
    <h2>Missing — HPOA only</h2>
    <span class="big">${missing.length.toLocaleString()}</span> associations <span class="muted">(≤25/disease)</span>
    <div class="small muted">${uniq(missing, "phenotype").toLocaleString()} distinct phenotypes · ${uniq(missing, "mondo").toLocaleString()} diseases</div>
  </div>
</div>

## Novel associations — dismech asserts, HPOA doesn't

```js
const novelSearch = view(Inputs.search(novel, {placeholder: "search by disease or phenotype…"}));
```

```js
Inputs.table(novelSearch, {
  sort: "depth",
  reverse: true,
  columns: ["disease", "mondo", "phenotype", "label", "depth"],
  header: {phenotype: "HP ID", label: "phenotype"},
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
    phenotype: (id) => htl.html`<a href=https://hpo.jax.org/browse/term/${id} target=_blank>${id}</a>`,
  },
})
```

## Missing associations — HPOA asserts, dismech doesn't

```js
const missingSearch = view(Inputs.search(missing, {placeholder: "search by disease or phenotype…"}));
```

```js
Inputs.table(missingSearch, {
  sort: "depth",
  reverse: true,
  columns: ["disease", "mondo", "phenotype", "label", "depth"],
  header: {phenotype: "HP ID", label: "phenotype"},
  format: {
    mondo: (id) => htl.html`<a href=https://monarchinitiative.org/${id} target=_blank>${id}</a>`,
    phenotype: (id) => htl.html`<a href=https://hpo.jax.org/browse/term/${id} target=_blank>${id}</a>`,
  },
})
```

<div class="small note">

Counts pool every matched disease, including **lineage** (grouping) matches whose
HPOA side is the union of subtype annotations — so a broad dismech grouping inflates
its *missing* list. Filter on the [per-disease](./diseases) page to read a single
disease in isolation.

</div>
