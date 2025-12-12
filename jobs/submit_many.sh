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
ENERGY_BASE="10000"
DERIV_TARGET="a"
EVENTS_PER_JOB="20000"
SEED_START=3000
SEED_END=3999

sanitize_token() {
  local token="$1"
  token=${token//:/c}
  token=${token//./p}
  token=${token//-/m}
  token=${token//+/p}
  echo "$token"
}

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --mode <ad|finite-diff>    Choose automatic-differentiation (default) or finite-difference mode.
  --epsilon <value>          Step size for finite-difference runs (default: ${EPSILON}).
  --a-base <value>           Base absorber thickness a (default: ${A_BASE}).
  --energy-base <value>      Base primary energy in MeV (default: ${ENERGY_BASE}).
  --deriv-target <a|energy>  Quantity to differentiate (default: ${DERIV_TARGET}).
  --num-events <value>       Number of events per job (default: ${EVENTS_PER_JOB}).
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
    --energy-base)
      ENERGY_BASE="$2"
      shift 2
      ;;
    --deriv-target)
      DERIV_TARGET="$2"
      shift 2
      ;;
    --num-events)
      EVENTS_PER_JOB="$2"
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

if [[ "$DERIV_TARGET" != "a" && "$DERIV_TARGET" != "energy" ]]; then
  echo "Unsupported deriv-target: ${DERIV_TARGET}. Expected 'a' or 'energy'." >&2
  exit 1
fi

if [[ "$MODE" == "ad" ]]; then
  if [[ "$DERIV_TARGET" == "energy" ]]; then
    RUN_LABEL="ad_energy_E$(sanitize_token "$ENERGY_BASE")"
  else
    RUN_LABEL="ad_a$(sanitize_token "$A_BASE")"
  fi
else
  if [[ "$DERIV_TARGET" == "energy" ]]; then
    RUN_LABEL="finite_diff_energy_E$(sanitize_token "$ENERGY_BASE")_eps$(sanitize_token "$EPSILON")"
  else
    RUN_LABEL="finite_diff_a$(sanitize_token "$A_BASE")_eps$(sanitize_token "$EPSILON")"
  fi
fi
if [[ "$DERIV_TARGET" != "energy" ]]; then
  RUN_LABEL="${RUN_LABEL}_E$(sanitize_token "$ENERGY_BASE")"
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
  if [[ "$DERIV_TARGET" == "energy" ]]; then
    if [[ "$ENERGY_BASE" == *:* ]]; then
      echo "Cannot use ':' in energy-base when running finite-diff on energy." >&2
      exit 1
    fi
    E_PLUS=$(awk -v base="$ENERGY_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base + eps }')
    E_MINUS=$(awk -v base="$ENERGY_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base - eps }')
  else
    A_PLUS=$(awk -v base="$A_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base + eps }')
    A_MINUS=$(awk -v base="$A_BASE" -v eps="$EPSILON" 'BEGIN { printf "%.6f", base - eps }')
  fi
fi

for SEED in $(seq "${SEED_START}" "${SEED_END}"); do
  if [[ "$MODE" == "ad" ]]; then
    FILE="$OUTDIR/edeps_${SEED}"
    if [[ ! -f "$FILE" ]]; then
      echo "Submitting AD job for missing seed $SEED"
      EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=1,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB}"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  else
    FILE_PLUS="$OUTDIR/edeps_${SEED}_plus"
    FILE_MINUS="$OUTDIR/edeps_${SEED}_minus"
    if [[ ! -f "$FILE_PLUS" ]]; then
      if [[ "$DERIV_TARGET" == "energy" ]]; then
        echo "Submitting finite-diff (+epsilon) job for seed $SEED (E=${E_PLUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=0,OUTPUT_SUFFIX=plus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${E_PLUS},EVENTS_PER_JOB=${EVENTS_PER_JOB}"
      else
        echo "Submitting finite-diff (+epsilon) job for seed $SEED (a=${A_PLUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_PLUS},USE_AD=0,OUTPUT_SUFFIX=plus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB}"
      fi
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
    if [[ ! -f "$FILE_MINUS" ]]; then
      if [[ "$DERIV_TARGET" == "energy" ]]; then
        echo "Submitting finite-diff (-epsilon) job for seed $SEED (E=${E_MINUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=0,OUTPUT_SUFFIX=minus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${E_MINUS},EVENTS_PER_JOB=${EVENTS_PER_JOB}"
      else
        echo "Submitting finite-diff (-epsilon) job for seed $SEED (a=${A_MINUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_MINUS},USE_AD=0,OUTPUT_SUFFIX=minus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB}"
      fi
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  fi
done
