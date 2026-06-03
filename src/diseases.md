# Per-disease

Every dismech **disease** (MONDO) — including those with no HPOA counterpart — as a
browsable index. Search or sort, then **click a card to expand its mini disease
page**: the phenotypes the two resources hold **in common**, and those **unique to
each**, inline. Counts here are phenotypes *for that one disease*; neither resource
is treated as correct.

```js
const perDisease = await FileAttachment("data/per_disease.json").json();
const MATCH_COLORS = {exact: "#4269d0", descendant: "#3ca951", ancestor: "#efb118", mixed: "#ff725c", "dismech-only": "#a463f2"};
```

<style>
.dlist { display: flex; flex-direction: column; gap: 6px; margin: 1rem 0; }
.drow { border: 1px solid var(--theme-foreground-faintest); border-radius: 8px; background: var(--theme-background-alt); overflow: hidden; }
.drow.open { border-color: #4269d0; }
.drow-head { display: grid; grid-template-columns: 1fr auto auto auto auto 1rem; align-items: center; gap: .75rem; padding: .5rem .8rem; cursor: pointer; }
.drow-head:hover { background: var(--theme-background); }
.drow-name { font-weight: 600; font-size: .85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.drow-mondo { font-size: .72rem; font-variant-numeric: tabular-nums; }
.drow-f1 { font-size: .78rem; font-variant-numeric: tabular-nums; }
.drow-diff { font-size: .74rem; font-variant-numeric: tabular-nums; }
.chev { color: var(--theme-foreground-muted); font-size: .7rem; }
.muted { color: var(--theme-foreground-muted); }
.badge { color: #fff; border-radius: 4px; padding: .05rem .4rem; font-size: .68rem; font-weight: 600; }
.ddetail { padding: .3rem 1rem 1rem; border-top: 1px solid var(--theme-foreground-faintest); }
.ddetail h3 { font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; color: var(--theme-foreground-muted); margin: .8rem 0 .35rem; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.4rem; }
.three-col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.4rem; }
@media (max-width: 760px) { .two-col, .three-col { grid-template-columns: 1fr; } }
.overlap-row { margin: .3rem 0 .2rem; max-width: 460px; }
.mbar { display: flex; align-items: center; gap: .5rem; font-size: .78rem; margin: .18rem 0; }
.mbar-l { width: 64px; color: var(--theme-foreground-muted); }
.mbar-track { flex: 1; height: 8px; background: var(--theme-foreground-faintest); border-radius: 4px; overflow: hidden; }
.mbar-fill { display: block; height: 100%; }
.mbar-v { width: 34px; text-align: right; font-variant-numeric: tabular-nums; }
.termlist { margin: 0; padding-left: 1.1rem; font-size: .8rem; columns: 1; }
.termlist li { margin: .12rem 0; }
.dmeta { font-size: .76rem; color: var(--theme-foreground-muted); margin-top: .2rem; }
</style>

```js
const query = view(Inputs.text({placeholder: "search disease or MONDO…", width: 300}));
const sortKey = view(
  Inputs.select(
    new Map([
      ["overlap (Jaccard) ↓", (a, b) => b.closure.jaccard - a.closure.jaccard],
      ["overlap (Jaccard) ↑", (a, b) => a.closure.jaccard - b.closure.jaccard],
      ["most shared phenotypes", (a, b) => b.n_shared - a.n_shared],
      ["most dismech-only", (a, b) => b.n_novel - a.n_novel],
      ["most HPOA-only", (a, b) => b.n_missing - a.n_missing],
      ["name", (a, b) => a.label.localeCompare(b.label)],
    ]),
    {label: "sort", value: (a, b) => b.closure.jaccard - a.closure.jaccard},
  ),
);
```

```js
const q = (query || "").toLowerCase().trim();
const filtered = perDisease
  .filter((d) => !q || d.label.toLowerCase().includes(q) || d.mondo.toLowerCase().includes(q))
  .sort(sortKey);
const CAP = 150;
```

```js
const expanded = Mutable(null);
const toggle = (m) => { expanded.value = expanded.value === m ? null : m; };
```

```js
function metricBar(label, value, color) {
  return html`<div class="mbar">
    <span class="mbar-l">${label}</span>
    <span class="mbar-track"><span class="mbar-fill" style=${`width:${Math.round(value * 100)}%;background:${color}`}></span></span>
    <span class="mbar-v">${value.toFixed(2)}</span>
  </div>`;
}

function termList(terms) {
  if (!terms.length) return html`<div class="muted" style="font-size:.8rem">none</div>`;
  return html`<ul class="termlist">${terms.map(
    (t) => html`<li><a href=${`https://hpo.jax.org/browse/term/${t.id}`} target=_blank>${t.label}</a> <span class="muted">d${t.depth}</span></li>`,
  )}</ul>`;
}

function diseaseDetail(d) {
  const c = MATCH_COLORS[d.match_type];
  const isOnly = d.match_type === "dismech-only";
  return html`<div class="ddetail">
    <div class="dmeta">
      ${d.n_dismech} dismech · ${d.n_hpoa} HPOA phenotypes${d.n_hpoa_nodes > 1 ? ` (across ${d.n_hpoa_nodes} MONDO nodes)` : ""}
      ${isOnly ? "" : `· ${d.more_specific} dismech finer / ${d.more_general} coarser · Resnik ${d.resnik_bma.toFixed(2)}`}
    </div>
    ${isOnly
      ? html`<div class="dmeta">No HPOA annotations for this disease — every phenotype below is unique to dismech.</div>`
      : html`<div class="overlap-row">
          ${metricBar("overlap", d.closure.jaccard, c)}
          ${metricBar("of dismech ⊂", d.closure.precision, c)}
          ${metricBar("of HPOA ⊂", d.closure.recall, c)}
          <div class="muted" style="font-size:.72rem;margin-top:.2rem">Jaccard overlap; the two shares read "of dismech's phenotypes, this fraction is also in HPOA" and vice-versa. Exact-ID overlap ${d.exact.jaccard.toFixed(2)} — hierarchy-aware credits agreement along the is-a lineage.</div>
        </div>`}
    <div class=${isOnly ? "" : "three-col"}>
      ${isOnly ? "" : html`<div><h3>In common · ${d.n_shared}</h3>${termList(d.shared_terms)}</div>`}
      <div><h3>${isOnly ? "dismech phenotypes" : "Unique to dismech"} · ${d.n_novel}</h3>${termList(d.novel_terms)}</div>
      ${isOnly ? "" : html`<div><h3>Unique to HPOA · ${d.n_missing}</h3>${termList(d.missing_terms)}</div>`}
    </div>
  </div>`;
}

function diseaseRow(d, exp) {
  const open = d.mondo === exp;
  const el = html`<div class=${`drow ${open ? "open" : ""}`}>
    <div class="drow-head">
      <span class="drow-name">${d.label}</span>
      <span class="badge" style=${`background:${MATCH_COLORS[d.match_type]}`}>${d.match_type}</span>
      <a class="drow-mondo" href=${`https://monarchinitiative.org/${d.mondo}`} target=_blank onclick=${(e) => e.stopPropagation()}>${d.mondo}</a>
      <span class="drow-f1">${d.match_type === "dismech-only" ? html`<span class="muted">no HPOA</span>` : html`∩ <b>${d.closure.jaccard.toFixed(2)}</b>`}</span>
      <span class="drow-diff muted" title="shared · unique to dismech · unique to HPOA">${d.n_shared}·${d.n_novel}·${d.n_missing}</span>
      <span class="chev">${open ? "▾" : "▸"}</span>
    </div>
    ${open ? diseaseDetail(d) : ""}
  </div>`;
  el.querySelector(".drow-head").onclick = () => toggle(d.mondo);
  return el;
}
```

```js
display(html`<div class="dlist">${filtered.slice(0, CAP).map((d) => diseaseRow(d, expanded))}</div>`);
display(
  filtered.length > CAP
    ? html`<div class="muted" style="font-size:.8rem">Showing ${CAP} of ${filtered.length} — refine the search to see more.</div>`
    : html`<div class="muted" style="font-size:.8rem">${filtered.length} diseases.</div>`,
);
```

<div class="small note">

Each card's **∩** is the hierarchy-aware **overlap** (Jaccard); the
`shared·dismech·HPOA` triple counts phenotypes in common, unique to dismech, and
unique to HPOA. Neither resource is treated as correct. Lineage (grouping) matches
union subtype annotations, so their HPOA side is large by construction — see
[coverage](./coverage) and [methods](./methods).

</div>
