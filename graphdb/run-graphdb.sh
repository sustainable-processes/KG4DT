#!/bin/sh
set -e

graphdb-repository-init "/repository.init"
repo-presparql-query "/repository.init" &

importrdf load -f -c /ontology/config.ttl /ontology/OntoMo.owl
graphdb "$@"