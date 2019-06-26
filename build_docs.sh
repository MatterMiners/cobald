#!/usr/bin/env bash
set -e

LIB_NAME=cobald
DOCS_DIR=docs

cd ${DOCS_DIR}
touch source/api/dummy
rm source/api/*
# export SPHINX_APIDOC_OPTIONS=members,undoc-members,no-show-inheritance
sphinx-apidoc --module-first --separate --implicit-namespaces --output-dir=source/api ../src/${LIB_NAME} --force && \
python3 $(which sphinx-build) -b html -d build/doctrees . build/html/ && \
open build/html/index.html
