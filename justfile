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
    [ -f hp.db ] || { curl -sL -o hp.db.gz "https://s3.amazonaws.com/bbop-sqlite/hp.db.gz"; gunzip -f hp.db.gz; }
    echo "fetched inputs:"; ls -la

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
