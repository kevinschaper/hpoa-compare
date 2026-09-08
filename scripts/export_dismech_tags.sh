#!/usr/bin/env bash
# Regenerate dismech's HPOA export for every release tag, from a sibling dismech
# checkout. dismech releases do not ship phenotype.dismech.hpoa as an asset, but
# the exporter is a pure kb/disorders YAML -> TSV projection, so we run the
# *current* exporter against each tag's kb/ (git archive) and cache the result
# under data/inputs/dismech/<tag>/. Also writes data/inputs/dismech/tags.tsv
# (tag, commit date, commit) which drives `hpoa-compare history`.
#
# Usage: scripts/export_dismech_tags.sh [path/to/dismech]   (default ../dismech)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DISMECH="$(cd "${1:-$ROOT/../dismech}" && pwd)"
OUT_ROOT="$ROOT/data/inputs/dismech"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT_ROOT"

git -C "$DISMECH" fetch --tags -q origin || echo "warning: could not fetch tags"
printf "tag\tdate\tcommit\n" > "$OUT_ROOT/tags.tsv"
for T in $(git -C "$DISMECH" tag --sort=creatordate); do
  D=$(git -C "$DISMECH" log -1 --format=%cs "$T")
  C=$(git -C "$DISMECH" rev-parse "$T^{commit}")
  printf "%s\t%s\t%s\n" "$T" "$D" "$C" >> "$OUT_ROOT/tags.tsv"
  OUT="$OUT_ROOT/$T"
  if [ -s "$OUT/phenotype.dismech.hpoa" ]; then continue; fi
  mkdir -p "$OUT" "$TMP/$T"
  git -C "$DISMECH" archive "$T" kb/disorders | tar -x -C "$TMP/$T"
  if ( cd "$DISMECH" && uv run python -m dismech.export.hpoa_export \
        --kb-dir "$TMP/$T/kb/disorders" --out-dir "$OUT" ) > "$OUT/export.log" 2>&1; then
    echo "$T $D $(grep -vc '^#' "$OUT/phenotype.dismech.hpoa") rows"
  else
    echo "$T FAILED (see $OUT/export.log)"; rm -f "$OUT/phenotype.dismech.hpoa"
  fi
  rm -rf "$TMP/$T"
done
LATEST=$(tail -1 "$OUT_ROOT/tags.tsv" | cut -f1)
cp "$OUT_ROOT/$LATEST/phenotype.dismech.hpoa" "$ROOT/data/inputs/phenotype.dismech.hpoa"
echo "current dismech export <- $LATEST"
