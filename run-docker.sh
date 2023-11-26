#!/usr/bin/env bash

bye () {
    echo "$@" >&2
    exit 1
}

self=$(realpath "$0")
self_dir=${self%/*}
self_name=${self##*/}

[[ -n $1 ]] || bye "Usage: ${self_name} <jtv file> [options]"
[[ -e $1 ]] || bye "no such file: '$1'" 
[[ -f $1 ]] || bye "'$1' is not a regular file"

jtv=$(realpath "$1")
shift

opt=(
    -it --rm --init
    -v "$jtv":/workdir/jtv.zip:ro
    -v "${self_dir}/jtv2xml.py":/workdir/script.py:ro
    -w /workdir
    python:alpine
    sh -c "python3 script.py ${*@Q} < jtv.zip"
)

docker run "${opt[@]}"
