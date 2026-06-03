# hpoa-compare tasks

# List recipes
default:
    @just --list

# Download pinned inputs (phenotype.hpoa, mondo.sssom.tsv, hp.db)
fetch:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p data/inputs
    cd data/inputs
    curl -sL -o phenotype.hpoa "https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/phenotype.hpoa"
    curl -sL -o mondo.sssom.tsv "https://purl.obolibrary.org/obo/mondo/mappings/mondo.sssom.tsv"
    # MONDO disease graph: take the release KGX (version-matched to the SSSOM);
    # semsql mondo.db lags the OBO release, so we do NOT use it for the disease axis.
    curl -sL -o mondo_edges.tsv "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo_edges.tsv"
    curl -sL -o mondo_nodes.tsv "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo_nodes.tsv"
    [ -f hp.db ] || { curl -sL -o hp.db.gz "https://s3.amazonaws.com/bbop-sqlite/hp.db.gz"; gunzip -f hp.db.gz; }
    echo "fetched inputs:"; ls -la
    @echo "verify checksums against data/MANIFEST.yaml before relying on a refresh"

# Copy the dismech HPOA export in from a sibling dismech checkout
import-dismech path="../hpoa-export/output/hpoa/phenotype.dismech.hpoa":
    cp {{ path }} data/inputs/phenotype.dismech.hpoa

# Run the comparison pipeline -> src/data/*.json
build:
    PYTHONPATH=pipeline uv run python -m hpoa_compare.cli build

# Python tests
test:
    PYTHONPATH=pipeline uv run --with pytest pytest pipeline/tests -q

# Install site deps and preview locally
dev:
    npm install && npm run dev

# Build the static site (runs the pipeline first)
site: build
    npm run build
