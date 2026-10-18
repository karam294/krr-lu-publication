#!/bin/sh
# Check the ontology with two reasoners (Session 3, slides 38-39), and its OWL profile.
#
#   docker compose --profile tools run --rm reasoner          (the reasoner service runs this file)
#
# ELK is fast but reads only the OWL 2 EL part; HermiT reads every axiom.
# ROBOT finds the imports through ontology/catalog-v001.xml. The whole run is
# saved in ontology/reasoner-run.txt, the evidence ontology/README.md asks for.
OUT=ontology/reasoner-run.txt
mkdir -p build
{
  echo "Reasoner run $(date -u +%Y-%m-%d), $(robot --version 2>/dev/null | grep -i 'robot version')"
  echo "Input: ontology/ontology.ttl ($(grep -o 'versionIRI <[^>]*>' ontology/ontology.ttl)), imports from ontology/imports/"
  for r in ELK HermiT; do
    echo
    echo "== $r"
    if robot reason --reasoner "$r" --input ontology/ontology.ttl --output "build/reasoned-$r.ttl" > "build/reason-$r.log" 2>&1; then
      echo "$r: consistent, no unsatisfiable classes"
    else
      grep -i "unsatisfiable" "build/reason-$r.log" | sed 's/.*ReasonerHelper - *//'
      echo "$r: PROBLEM. Why (the axioms that cause it, as Protege's ? button shows them):"
      robot explain --reasoner "$r" --input ontology/ontology.ttl --mode unsatisfiability \
        --unsatisfiable all --explanation "build/explain-$r.md" > /dev/null 2>&1
      sed -n '1,/^# Axiom Impact/p' "build/explain-$r.md" | grep -v '^# Axiom Impact'
    fi
  done
  echo
  echo "== OWL 2 DL profile of our own file (the imports left out)"
  grep -v "owl:imports" ontology/ontology.ttl > build/own-only.ttl
  robot validate-profile --profile DL --input build/own-only.ttl --output build/profile-own.txt > /dev/null 2>&1
  cat build/profile-own.txt
  echo
  echo "== OWL 2 DL profile with the imports"
  robot validate-profile --profile DL --input ontology/ontology.ttl --output build/profile-all.txt > /dev/null 2>&1
  head -1 build/profile-all.txt
  echo "$(($(wc -l < build/profile-all.txt) - 1)) violations: $(grep -c 'OntologyIRI(<https://ul.edu.lb/kr/pub>)' build/profile-all.txt) on Dublin Core terms our file uses and FaBiO declares another way, the rest inside FaBiO (build/profile-all.txt)"
} | tee "$OUT"