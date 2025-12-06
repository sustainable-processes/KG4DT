#!/bin/bash
cp ./graphdb/ontology/OntoMo.owl ./graphdb/ontology/OntoMo_out.owl
for patch in ./graphdb/ontology/patches/*.json; do
    python ./graphdb/ontology/patch_onto.py --in_rdf ./graphdb/ontology/OntoMo_out.owl --out_rdf ./graphdb/ontology/OntoMo_out_tmp.owl --json $patch
    mv ./graphdb/ontology/OntoMo_out_tmp.owl ./graphdb/ontology/OntoMo_out.owl
done