"""Extract obsolete-MONDO -> replacement-MONDO pairs from a mondo.obo file.

Usage: python scripts/extract_replaced_by.py <mondo.obo> <out.tsv>

The KGX node table carries only a `deprecated` flag, not the replacement target,
so we read `replaced_by:` tags from the OBO. Output is a small, stable TSV that
is committed (data/mondo_replaced_by.tsv) and consumed by the pipeline to
redirect stale SSSOM mappings onto live disease terms.
"""
import sys


def main(obo_path: str, out_path: str) -> int:
    cur = None
    pairs: dict[str, str] = {}
    with open(obo_path) as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line == "[Term]":
                cur = None
            elif line.startswith("id: MONDO:"):
                cur = line[len("id: "):]
            elif line.startswith("replaced_by: MONDO:") and cur:
                pairs[cur] = line[len("replaced_by: "):]
    with open(out_path, "w") as f:
        f.write("obsolete\treplacement\n")
        for obsolete, replacement in sorted(pairs.items()):
            f.write(f"{obsolete}\t{replacement}\n")
    print(f"wrote {out_path} ({len(pairs)} pairs)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
