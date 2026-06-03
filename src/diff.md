# Novel & missing

The actionable term-level differences. **Novel** = a dismech HP term with no
ancestor or descendant among the disease's HPOA annotations — a candidate new
association (or a curation error to check). **Missing** = an HPOA term with no
ancestor/descendant in dismech — a recall gap. Terms are ranked by **depth**
(longest is-a path from *Phenotypic abnormality* — deeper = more specific); up to
25 per disease are listed.

```js
const perDisease = await FileAttachment("data/per_disease.json").json();
```

```js
const novel = perDisease.flatMap((d) =>
  d.novel_terms.map((t) => ({disease: d.label, mondo: d.mondo, term: t.id, label: t.label, depth: t.depth})),
);
const missing = perDisease.flatMap((d) =>
  d.missing_terms.map((t) => ({disease: d.label, mondo: d.mondo, term: t.id, label: t.label, depth: t.depth})),
);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Novel dismech terms</h2>
    <span class="big">${novel.length.toLocaleString()}</span> listed
  </div>
  <div class="card">
    <h2>Missing HPOA terms</h2>
    <span class="big">${missing.length.toLocaleString()}</span> listed (top-25/disease)
  </div>
</div>

## Novel — dismech says, HPOA doesn't

```js
const novelSearch = view(Inputs.search(novel, {placeholder: "search novel terms…"}));
```

```js
Inputs.table(novelSearch, {
  sort: "depth",
  reverse: true,
  format: {
    term: (id) => htl.html`<a href=https://hpo.jax.org/browse/term/${id} target=_blank>${id}</a>`,
  },
})
```

## Missing — HPOA says, dismech doesn't

```js
const missingSearch = view(Inputs.search(missing, {placeholder: "search missing terms…"}));
```

```js
Inputs.table(missingSearch, {
  sort: "depth",
  reverse: true,
  format: {
    term: (id) => htl.html`<a href=https://hpo.jax.org/browse/term/${id} target=_blank>${id}</a>`,
  },
})
```
