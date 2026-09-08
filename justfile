# hpoa-compare tasks

# HPO releases to keep for the release history (paired to dismech tags by date).
hpo_releases := "2025-11-24 2026-01-08 2026-02-16 2026-06-06 2026-06-23 2026-09-01"

# List recipes
default:
    @just --list

# Download pinned inputs: MONDO (SSSOM + release KGX graph), hp.obo, and every HPO release in `hpo_releases`
fetch:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p data/inputs/hpoa
    cd data/inputs
    curl -sL -o mondo.sssom.tsv "https://purl.obolibrary.org/obo/mondo/mappings/mondo.sssom.tsv"
    # MONDO disease graph: take the release KGX (version-matched to the SSSOM);
    # semsql mondo.db lags the OBO release, so we do NOT use it for the disease axis.
    curl -sL -o mondo_edges.tsv "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo_edges.tsv"
    curl -sL -o mondo_nodes.tsv "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo_nodes.tsv"
    for V in {{ hpo_releases }}; do
        mkdir -p hpoa/$V
        [ -s hpoa/$V/phenotype.hpoa ] || curl -sL -o hpoa/$V/phenotype.hpoa \
            "https://github.com/obophenotype/human-phenotype-ontology/releases/download/v$V/phenotype.hpoa"
    done
    LATEST=$(echo {{ hpo_releases }} | tr ' ' '\n' | sort | tail -1)
    cp hpoa/$LATEST/phenotype.hpoa phenotype.hpoa
    # phenotype axis: the release hp.obo, version-matched to the newest phenotype.hpoa
    curl -sL -o hp.obo "https://github.com/obophenotype/human-phenotype-ontology/releases/download/v$LATEST/hp.obo"
    echo "fetched inputs:"; ls -la . hpoa/*

# Re-derive data/mondo_replaced_by.tsv from the release mondo.obo (replaced_by tags)
refresh-replaced-by:
    curl -sL -o /tmp/mondo.obo "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo"
    python3 scripts/extract_replaced_by.py /tmp/mondo.obo data/mondo_replaced_by.tsv
    @echo "verify checksums against data/MANIFEST.yaml before relying on a refresh"

# Regenerate phenotype.dismech.hpoa for every dismech release tag (cached) from a sibling checkout
export-dismech dismech="../dismech":
    scripts/export_dismech_tags.sh {{ dismech }}

# Run the comparison on the current pair -> src/data/*.json
build:
    PYTHONPATH=pipeline uv run python -m hpoa_compare.cli build

# Compare every dismech release against its contemporary HPOA -> src/data/history.*
history *args:
    PYTHONPATH=pipeline uv run python -m hpoa_compare.cli history {{ args }}

# Python tests
test:
    PYTHONPATH=pipeline uv run --with pytest pytest pipeline/tests -q

# Install site deps and preview locally
dev:
    npm install && npm run dev

# Build the static site (runs the pipeline first)
site: build history
    npm run build
