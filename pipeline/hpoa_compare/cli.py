"""Build the comparison artifacts consumed by the Observable Framework site."""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import click

from . import compare
from . import frequency as freq

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "data" / "inputs"
HISTORY = ROOT / "data" / "history"          # per-release cache (committed)
ARTIFACTS = ROOT / "src" / "data"
REPLACED_BY = ROOT / "data" / "mondo_replaced_by.tsv"


def _write(name: str, obj) -> None:
    path = ARTIFACTS / name
    path.write_text(json.dumps(obj, indent=2))
    click.echo(f"  wrote {path.relative_to(ROOT)}")


def _load_context() -> compare.Context:
    click.echo("loading MONDO map + graph and HPO graph...")
    ctx = compare.load_context(INPUTS, REPLACED_BY)
    click.echo(f"  context {ctx.key}")
    return ctx


@click.group()
def cli() -> None:
    """hpoa-compare pipeline."""


@cli.command()
def build() -> None:
    """Compare the current pair of inputs and emit src/data/*.json."""
    ctx = _load_context()
    click.echo("comparing current inputs...")
    res = compare.compare_files(
        ctx, INPUTS / "phenotype.dismech.hpoa", INPUTS / "phenotype.hpoa", keep_diffs=True,
    )
    frequency_report = {
        "band_order": [freq.BAND_LABEL[b] for b in freq.BANDS],
        "summary": res.frequency_summary,
        "disagreements": res.frequency_disagreements,
    }
    versions = {
        "dismech": res.dismech_header.get("version", ""),
        "dismech_tag": _current_dismech_tag(),
        "dismech_date": res.dismech_header.get("date", ""),
        "hpoa": res.hpoa_header.get("version", ""),
        "hpo": ctx.hpo.version,
        "built": date.today().isoformat(),
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    click.echo("writing artifacts...")
    _write("coverage.json", res.coverage)
    _write("aggregates.json", res.aggregates)
    _write("per_disease.json", [c.to_row() for c in res.browser])
    _write("disease_coverage.json", res.disease_coverage)
    _write("frequency.json", frequency_report)
    _write("versions.json", versions)

    cov, agg = res.coverage, res.aggregates
    click.echo(
        f"\nMONDO coverage: {cov['exact_shared']} exact-shared + {cov['lineage_shared']} "
        f"lineage-shared | {cov['dismech_only']} dismech-only | {cov['hpoa_only']} HPOA-only\n"
        f"phenotype overlap (exact disease matches): closure Jaccard "
        f"{agg['closure']['micro']['jaccard']} (exact {agg['exact']['micro']['jaccard']})"
    )


def _current_dismech_tag() -> str:
    """The dismech release tag whose export is byte-identical to the current input."""
    import hashlib
    cur = INPUTS / "phenotype.dismech.hpoa"
    tags_dir = INPUTS / "dismech"
    if not (cur.exists() and (tags_dir / "tags.tsv").exists()):
        return ""
    digest = hashlib.sha256(cur.read_bytes()).hexdigest()
    for t in reversed(_read_tags()):
        f = tags_dir / t["tag"] / "phenotype.dismech.hpoa"
        if f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == digest:
            return t["tag"]
    return ""


def _read_tags() -> list[dict[str, str]]:
    with open(INPUTS / "dismech" / "tags.tsv", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return sorted(rows, key=lambda r: (r["date"], r["tag"]))


def _hpoa_releases() -> list[str]:
    return sorted(p.name for p in (INPUTS / "hpoa").iterdir()
                  if (p / "phenotype.hpoa").exists())


def pair_hpoa_release(tag_date: str, releases: list[str]) -> str:
    """Newest HPO release on or before ``tag_date`` (else the oldest available)."""
    eligible = [r for r in releases if r <= tag_date]
    return eligible[-1] if eligible else releases[0]


@cli.command()
@click.option("--force", is_flag=True, help="recompute every release, ignoring the cache")
@click.option("--tag", "only", multiple=True, help="restrict to these dismech tags")
def history(force: bool, only: tuple[str, ...]) -> None:
    """Compare every dismech release against its contemporary HPOA; emit history."""
    import duckdb
    import pandas as pd

    tags = _read_tags()
    if only:
        tags = [t for t in tags if t["tag"] in only]
    releases = _hpoa_releases()
    HISTORY.mkdir(parents=True, exist_ok=True)
    ctx: compare.Context | None = None

    for t in tags:
        tag, tag_date = t["tag"], t["date"]
        dismech_path = INPUTS / "dismech" / tag / "phenotype.dismech.hpoa"
        if not dismech_path.exists():
            click.echo(f"  {tag}: no export, skipping")
            continue
        hpoa_rel = pair_hpoa_release(tag_date, releases)
        meta_path = HISTORY / f"{tag}.json"
        pq_path = HISTORY / f"{tag}.parquet"
        if ctx is None:
            ctx = _load_context()
        if not force and meta_path.exists() and pq_path.exists():
            cached = json.loads(meta_path.read_text())
            if cached.get("context_key") == ctx.key and cached.get("hpoa_release") == hpoa_rel:
                click.echo(f"  {tag} ({tag_date}) cached")
                continue
        click.echo(f"  {tag} ({tag_date}) vs HPOA {hpoa_rel} ...", nl=False)
        res = compare.compare_files(
            ctx, dismech_path, INPUTS / "hpoa" / hpoa_rel / "phenotype.hpoa", keep_diffs=False,
        )
        rows = [{"release": tag, "release_date": tag_date, "hpoa_release": hpoa_rel,
                 **compare.history_rows(c)} for c in res.browser]
        df = pd.DataFrame(rows)  # noqa: F841  (DuckDB reads it by name below)
        duckdb.sql("COPY (SELECT * FROM df ORDER BY mondo) TO '{}' (FORMAT PARQUET)".format(pq_path))
        meta = {
            "release": tag, "release_date": tag_date, "commit": t.get("commit", ""),
            "hpoa_release": hpoa_rel, "hpoa_version": res.hpoa_header.get("version", ""),
            "dismech_version": res.dismech_header.get("version", ""),
            "context_key": ctx.key,
            **compare.release_totals(res),
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        click.echo(f" {res.coverage['dismech_diseases']} diseases, "
                   f"closure Jaccard {res.aggregates['closure']['micro']['jaccard']}")

    # --- combine per-release caches into the site artifacts (DuckDB) ---
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_pq = ARTIFACTS / "history.parquet"
    duckdb.sql(
        f"COPY (SELECT * FROM read_parquet('{HISTORY}/*.parquet') "
        f"ORDER BY release_date, release, mondo) TO '{out_pq}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    click.echo(f"  wrote {out_pq.relative_to(ROOT)}")
    metas = sorted(
        (json.loads(p.read_text()) for p in HISTORY.glob("*.json")),
        key=lambda m: (m["release_date"], m["release"]),
    )
    _write("history_releases.json", metas)
    n = duckdb.sql(f"SELECT count(*), count(DISTINCT release) FROM '{out_pq}'").fetchone()
    click.echo(f"\nhistory: {n[1]} releases, {n[0]} disease-release rows")


if __name__ == "__main__":
    cli()
