#!/usr/bin/env bash

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

cat "$SCRIPTPATH/../figgy/config/constants.py"| grep -E "VERSION\s+=\s+" | grep -v "AUDIT" | sed -E "s#.*([0-9]+.[0-9]+.[0-9]+[a-zA-Z]?).*#\1#g"