#!/bin/bash
#SBATCH --job-name=testem3
#SBATCH --output=/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build/logs/testem3/job_%j.out
#SBATCH --error=/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build/logs/testem3/job_%j.err
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=2G
#SBATCH --account=atlas:usatlas
#SBATCH --partition=roma
#SBATCH --chdir=/fs/ddn/sdf/group/atlas/d/jkrupa/hepemshow_reproductionattempt1/hepemshow/build

# Expect SEED and OUTDIR from --export
: "${SEED:?need SEED}"; : "${OUTDIR:?need OUTDIR}"

A_VALUE=${A_VALUE:-2.3}
USE_AD=${USE_AD:-1}
OUTPUT_SUFFIX=${OUTPUT_SUFFIX:-}
KE_CUT=${KE_CUT:-}
THRESHOLD=${THRESHOLD:-}
THRESHOLD2=${THRESHOLD2:--1.}
DERIV_TARGET=${DERIV_TARGET:-a}
ENERGY_VALUE=${ENERGY_VALUE:-10000}
EVENTS_PER_JOB=${EVENTS_PER_JOB:-20000}

./hepemshow_utils/jobs/run_testem3.sh "$SEED" "$OUTDIR" "$A_VALUE" "$USE_AD" "$OUTPUT_SUFFIX" "$KE_CUT" "$THRESHOLD" "$THRESHOLD2" "$DERIV_TARGET" "$ENERGY_VALUE" "$EVENTS_PER_JOB"
