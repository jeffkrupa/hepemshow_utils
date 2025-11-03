#!/bin/bash
# Arguments: SEED OUTDIR [A_VALUE] [USE_AD] [OUTPUT_SUFFIX] [KE_CUT] [THRESHOLD] [THRESHOLD2]

SEED=$1
OUTDIR=$2
A_VALUE=${3:-2.3}
USE_AD=${4:-1}
OUTPUT_SUFFIX=${5:-""}
KE_CUT=${6:-""}
THRESHOLD=${7:-""}
THRESHOLD2=${8:-"-1."}

if [[ "$USE_AD" == "1" ]]; then
    A_ARG="${A_VALUE}:1"
else
    A_ARG="${A_VALUE}"
fi

WORKDIR=/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build

cd $WORKDIR || { echo "Directory not found: $WORKDIR"; exit 1; }

# Run the simulation
CMD=(./HepEmShow -n 20000 -s "${SEED}" -a "${A_ARG}" -e 10000 --stop-grad-mode 2)
if [[ -n "$THRESHOLD" ]]; then
    CMD+=(-f "${THRESHOLD}")
fi
if [[ -n "$THRESHOLD2" ]]; then
    CMD+=(-k "${THRESHOLD2}")
fi
if [[ -n "$KE_CUT" ]]; then
    CMD+=(-c "${KE_CUT}")
fi
"${CMD[@]}"

# Move the output file
OUTFILE=edeps_${SEED}
TARGET_FILE="$OUTFILE"
if [[ -n "$OUTPUT_SUFFIX" ]]; then
    TARGET_FILE="${TARGET_FILE}_${OUTPUT_SUFFIX}"
fi

if [ -f "$OUTFILE" ]; then
    mkdir -p "$OUTDIR"
    mv "$OUTFILE" "$OUTDIR/${TARGET_FILE}"
    echo "Moved $OUTFILE to $OUTDIR/${TARGET_FILE}"
else
    echo "Error: $OUTFILE not found!"
    exit 2
fi
