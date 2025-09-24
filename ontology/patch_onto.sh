#!/bin/bash
cp ./ontology/OntoMo.owl ./ontology/OntoMo_out.owl
for patch in ./ontology/patches/*.json; do
    python ./ontology/patch_onto.py --in_rdf ./ontology/OntoMo_out.owl --out_rdf ./ontology/OntoMo_out_tmp.owl --json $patch
    mv ./ontology/OntoMo_out_tmp.owl ./ontology/OntoMo_out.owl
done