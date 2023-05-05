#!/bin/bash

# Change to base directory
BASEDIR=$(cd $(dirname $0)/../.. || exit ; pwd)
FEDBIOMED_DIR="$BASEDIR"/fedbiomed

while :
  do
    case "$1" in
      -bd | --build | build )
        BUILD=1
        shift 1
        ;;
      -s | --serve | serve )
        SERVE=1
        shift 1
        ;;
      -h | --help)
        exit 2
        ;;
      *)
        ARGS="$@"
        break
        ;;
    esac
  done



if [ -n "$BUILD" ] && [ -n "$SERVE" ]; then
    echo "ERROR: Please only SERVE or BUILD"
    exit 1
fi

if [ -z "$SERVE" ] && [ -z "$BUILD" ]; then
    echo "ERROR: Missing command please use --build or --serve"
    exit 1
fi


export PYTHONPATH=$FEDBIOMED_DIR


if [ -n "$SERVE" ]; then
  mkdocs serve ${ARGS}
elif [ -n "$BUILD" ]; then
  mkdocs build ${ARGS}
fi
