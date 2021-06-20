#!/usr/bin/env bash
# formats any soundfile to the format required by pysndfx (16k samplign rate, floaot32 for the PCM notation)
sox "$1" -c 1 -r 16000 -e floating-point "$2"
