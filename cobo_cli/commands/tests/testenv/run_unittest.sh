#!/bin/bash

# 'testenv' moved from ${PROJ_ROOT} to ${PROJ_ROOT}/tests

SCRIPT=$(readlink -f "$0")
# tests/testenv
TESTENV=$(dirname "$SCRIPT")
# tests
BASEDIR=$(dirname "$TESTENV")
PROJECT_DIR=$(dirname "$BASEDIR")

CONF=$TESTENV/tox_ut.ini
WORKDIR=$PROJECT_DIR/.tox

ARG=$1
OPTS="-c $CONF --workdir $WORKDIR"

if [ "$ARG" == "-r" ]; then
    OPTS="$OPTS -r"
fi

tox $OPTS
