#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR=${OUTDIR:-}
LOGDIR=${LOGDIR:-}
KE_CUT=""
THRESHOLD=""
THRESHOLD2="-1."
MODE="ad"
EPSILON="0.01"
A_BASE="2.3"
SEED_START=3000
SEED_END=3999

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --mode <ad|finite-diff>    Choose automatic-differentiation (default) or finite-difference mode.
  --epsilon <value>          Step size for finite-difference runs (default: ${EPSILON}).
  --a-base <value>           Base absorber thickness a (default: ${A_BASE}).
  --seed-range <start:end>   Inclusive seed range (default: ${SEED_START}:${SEED_END}).
  --outdir <path>            Override output directory (defaults to an auto-derived path).
  --logdir <path>            Override log directory (defaults to an auto-derived path).
  --ke-cut <value>           Enable kinetic-energy cut at <value> MeV (omit to disable).
  --threshold <value>        Override energy-deposition threshold (omits flag when unset).
  --threshold2 <value>       Override secondary threshold (default: ${THRESHOLD2}).
  -h, --help                 Show this help message and exit.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --epsilon)
      EPSILON="$2"
      shift 2
      ;;
    --a-base)
      A_BASE="$2"
      shift 2
      ;;
    --seed-range)
      RANGE="$2"
      IFS=":" read -r SEED_START SEED_END <<<"$RANGE"
      shift 2
      ;;
    --outdir)
      OUTDIR="$2"
      shift 2
      ;;
    --logdir)
      LOGDIR="$2"
      shift 2
      ;;
    --ke-cut)
      KE_CUT="$2"
      shift 2
      ;;
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --threshold2)
      THRESHOLD2="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "ad" && "$MODE" != "finite-diff" ]]; then
  echo "Unsupported mode: ${MODE}. Expected 'ad' or 'finite-diff'." >&2
  exit 1
fi

if [[ "$MODE" == "ad" ]]; then
  RUN_LABEL="ad_a${A_BASE}"
else
  RUN_LABEL="finite_diff_a${A_BASE}_eps${EPSILON}"
fi
if [[ -n "$KE_CUT" ]]; then
  KE_TAG=${KE_CUT//./p}
  RUN_LABEL="${RUN_LABEL}_kecut${KE_TAG}"
fi
if [[ -n "$THRESHOLD" ]]; then
  THR_TAG=${THRESHOLD//./p}
  RUN_LABEL="${RUN_LABEL}_thr${THR_TAG}"
fi
if [[ "$THRESHOLD2" != "-1." && -n "$THRESHOLD2" ]]; then
  T2_TAG=${THRESHOLD2//./p}
  RUN_LABEL="${RUN_LABEL}_thr2${T2_TAG}"
fi

if [[ -z "$OUTDIR" ]]; then
  OUTDIR="${SCRIPT_DIR}/outputs/${RUN_LABEL}"
fi
if [[ -z "$LOGDIR" ]]; then
  LOGDIR="${SCRIPT_DIR}/logs/testem3/${RUN_LABEL}"
fi

mkdir -p "$LOGDIR" "$OUTDIR"

COMMON_SBATCH_ARGS=(--output="${LOGDIR}/job_%j.out" --error="${LOGDIR}/job_%j.err")

if [[ "$MODE" == "finite-diff" ]]; then
  A_PLUS=$(awk -v base="$A_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base + eps }')
  A_MINUS=$(awk -v base="$A_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base - eps }')
fi

for SEED in $(seq "${SEED_START}" "${SEED_END}"); do
  if [[ "$MODE" == "ad" ]]; then
    FILE="$OUTDIR/edeps_${SEED}"
    if [[ ! -f "$FILE" ]]; then
      echo "Submitting AD job for missing seed $SEED"
      EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=1"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  else
    FILE_PLUS="$OUTDIR/edeps_${SEED}_plus"
    FILE_MINUS="$OUTDIR/edeps_${SEED}_minus"
    if [[ ! -f "$FILE_PLUS" ]]; then
      echo "Submitting finite-diff (+epsilon) job for seed $SEED (a=${A_PLUS})"
      EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_PLUS},USE_AD=0,OUTPUT_SUFFIX=plus"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
    if [[ ! -f "$FILE_MINUS" ]]; then
      echo "Submitting finite-diff (-epsilon) job for seed $SEED (a=${A_MINUS})"
      EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_MINUS},USE_AD=0,OUTPUT_SUFFIX=minus"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  fi
done
