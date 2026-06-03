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
    cd ../.. && just refresh-replaced-by

# Re-derive data/mondo_replaced_by.tsv from the release mondo.obo (replaced_by tags)
refresh-replaced-by:
    #!/usr/bin/env bash
    set -euo pipefail
    curl -sL -o /tmp/mondo.obo "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo"
    python3 -c "
import sys
cur=None; pairs={}
for line in open('/tmp/mondo.obo'):
    line=line.rstrip()
    if line=='[Term]': cur=None
    elif line.startswith('id: MONDO:'): cur=line[4:]
    elif line.startswith('replaced_by: MONDO:') and cur: pairs[cur]=line[13:]
with open('data/mondo_replaced_by.tsv','w') as f:
    f.write('obsolete\treplacement\n')
    for k,v in sorted(pairs.items()): f.write(f'{k}\t{v}\n')
print(f'wrote data/mondo_replaced_by.tsv ({len(pairs)} pairs)')
"
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
