#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR=${OUTDIR:-}
LOGDIR=${LOGDIR:-}
KE_CUT=""
THRESHOLD=""
THRESHOLD2="-1."
GRAZING_STOP_TRACK="1"
BACKWARD_BOUNDARY_STOP=""
MSC_DISPLACEMENT=""
MSC_STEP_RANDOM=""
BOUNDARY_TOLERANCE=""
MSC_DISP_SAFE_FLOOR=""
STOP_GRAD_MODE="2"
SAME_BOUNDARY_STOP=""
SAME_BOUNDARY_POS_TOL=""
SAME_BOUNDARY_MIN_FLIPS=""
SAME_BOUNDARY_FULL_TRACK=""
SAME_BOUNDARY_HARD_STOP=""
NUMIA_MFP_FLOOR=""
GAMMA_NUMIA_MFP_FLOOR=""
GAMMA_MFP_CAP=""
GAMMA_PE_EKIN_FLOOR=""
BOX_DIR_DEN_FLOOR=""
ROTATE_UP_FLOOR=""
CONVERSION_REG_EPS=""
UMSC_COS_DEN_FLOOR=""
UMSC_TAU_BLEND_EPS=""
UMSC_SIMPLE_DEN_FLOOR=""
UMSC_DISP_RAD_FLOOR=""
FULL_SANITIZE_STOPGRAD=""
SUFFIX=""
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
  --threshold <value>        Set |vx| grazing threshold passed as -f (omits flag when unset).
  --threshold2 <value>       Set near-boundary safety [mm] passed as -k (default: ${THRESHOLD2}).
  --grazing-stop-track <0|1> Set -y policy: 1=full-track stopgrad on grazing, 0=step-local sanitize (default: ${GRAZING_STOP_TRACK}).
  --backward-boundary-stop <0|1> Set -B policy: 1=unsafe trigger for boundary-limited backward vx<0, 0=disable.
  --msc-displacement <0|1>   Pass -m to enable/disable MSC lateral displacement.
  --msc-step-random <0|1>    Pass -r to enable/disable UMSC step-limit randomization.
  --boundary-tolerance <val> Pass -u boundary tolerance [mm].
  --msc-disp-safe-floor <v>  Pass -w post-step safety floor [mm] for displacement clipping.
  --stop-grad-mode <0|1|2>   Pass --stop-grad-mode to HepEmShow (default: ${STOP_GRAD_MODE}).
  --same-boundary-stop <N>   Pass -q: stop-grad when same x-boundary is hit N times over track history (0/off if unset).
  --same-boundary-pos-tol <v> Pass -z tolerance [mm] for same-boundary matching.
  --same-boundary-min-flips <N> Pass -j minimum vx sign flips on same boundary over track history.
  --same-boundary-full-track <0|1> Pass -o: full-track stopgrad on same-boundary trigger.
  --same-boundary-hard-stop <N> Pass -i: force full-track stopgrad if total hits on same boundary reach N.
  --numia-mfp-floor <v>    Pass -A: derivative-only mfp floor [mm] for UpdateNumIALeft.
  --gamma-numia-mfp-floor <v> Pass -T: derivative-only mfp floor [mm] for Gamma UpdateNumIALeft.
  --gamma-mfp-cap <v>     Pass -C: derivative-only mfp cap [mm] for Gamma HowFar step-limit product.
  --gamma-pe-ekin-floor <v> Pass -U: derivative-only ekin floor [MeV] for 1/ekin in gamma photoelectric xsec.
  --box-dir-den-floor <v> Pass -V: derivative-only signed floor for Box::DistanceToOut direction denominators.
  --rotate-up-floor <v>    Pass -F: derivative-only floor for RotateToReferenceFrame denominator.
  --conversion-reg-eps <v> Pass -N: derivative-only epsilon for MSC true/geom conversion regularization.
  --umsc-cos-den-floor <v> Pass -P: derivative-only denominator floor in UMSC SampleCosineTheta.
  --umsc-tau-blend-eps <v> Pass -Q: derivative-only smoothing width around UMSC tau branch threshold.
  --umsc-simple-den-floor <v> Pass -R: derivative-only denominator floor in UMSC SimpleScattering.
  --umsc-disp-rad-floor <v> Pass -S: derivative-only floor for UMSC displacement sqrt-radicand derivative.
  --full-sanitize-stopgrad <0|1> Pass -G: 1=also stop_grad GStepLength+Safety in DisableTrackGradient, 0=position+direction only.
  --suffix <text>            Append _<text> to the run label (output/log paths).
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
    --grazing-stop-track)
      GRAZING_STOP_TRACK="$2"
      shift 2
      ;;
    --backward-boundary-stop)
      BACKWARD_BOUNDARY_STOP="$2"
      shift 2
      ;;
    --msc-displacement)
      MSC_DISPLACEMENT="$2"
      shift 2
      ;;
    --msc-step-random)
      MSC_STEP_RANDOM="$2"
      shift 2
      ;;
    --boundary-tolerance)
      BOUNDARY_TOLERANCE="$2"
      shift 2
      ;;
    --msc-disp-safe-floor)
      MSC_DISP_SAFE_FLOOR="$2"
      shift 2
      ;;
    --stop-grad-mode)
      STOP_GRAD_MODE="$2"
      shift 2
      ;;
    --same-boundary-stop)
      SAME_BOUNDARY_STOP="$2"
      shift 2
      ;;
    --same-boundary-pos-tol)
      SAME_BOUNDARY_POS_TOL="$2"
      shift 2
      ;;
    --same-boundary-min-flips)
      SAME_BOUNDARY_MIN_FLIPS="$2"
      shift 2
      ;;
    --same-boundary-full-track)
      SAME_BOUNDARY_FULL_TRACK="$2"
      shift 2
      ;;
    --same-boundary-hard-stop)
      SAME_BOUNDARY_HARD_STOP="$2"
      shift 2
      ;;
    --numia-mfp-floor)
      NUMIA_MFP_FLOOR="$2"
      shift 2
      ;;
    --gamma-numia-mfp-floor)
      GAMMA_NUMIA_MFP_FLOOR="$2"
      shift 2
      ;;
    --gamma-mfp-cap)
      GAMMA_MFP_CAP="$2"
      shift 2
      ;;
    --gamma-pe-ekin-floor)
      GAMMA_PE_EKIN_FLOOR="$2"
      shift 2
      ;;
    --box-dir-den-floor)
      BOX_DIR_DEN_FLOOR="$2"
      shift 2
      ;;
    --rotate-up-floor)
      ROTATE_UP_FLOOR="$2"
      shift 2
      ;;
    --conversion-reg-eps)
      CONVERSION_REG_EPS="$2"
      shift 2
      ;;
    --umsc-cos-den-floor)
      UMSC_COS_DEN_FLOOR="$2"
      shift 2
      ;;
    --umsc-tau-blend-eps)
      UMSC_TAU_BLEND_EPS="$2"
      shift 2
      ;;
    --umsc-simple-den-floor)
      UMSC_SIMPLE_DEN_FLOOR="$2"
      shift 2
      ;;
    --umsc-disp-rad-floor)
      UMSC_DISP_RAD_FLOOR="$2"
      shift 2
      ;;
    --full-sanitize-stopgrad)
      FULL_SANITIZE_STOPGRAD="$2"
      shift 2
      ;;
    --suffix)
      SUFFIX="$2"
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

if [[ "$GRAZING_STOP_TRACK" != "0" && "$GRAZING_STOP_TRACK" != "1" ]]; then
  echo "Unsupported grazing-stop-track: ${GRAZING_STOP_TRACK}. Expected 0 or 1." >&2
  exit 1
fi
if [[ -n "$BACKWARD_BOUNDARY_STOP" && "$BACKWARD_BOUNDARY_STOP" != "0" && "$BACKWARD_BOUNDARY_STOP" != "1" ]]; then
  echo "Unsupported backward-boundary-stop: ${BACKWARD_BOUNDARY_STOP}. Expected 0 or 1." >&2
  exit 1
fi
if [[ -n "$FULL_SANITIZE_STOPGRAD" && "$FULL_SANITIZE_STOPGRAD" != "0" && "$FULL_SANITIZE_STOPGRAD" != "1" ]]; then
  echo "Unsupported full-sanitize-stopgrad: ${FULL_SANITIZE_STOPGRAD}. Expected 0 or 1." >&2
  exit 1
fi
if [[ -n "$MSC_DISPLACEMENT" && "$MSC_DISPLACEMENT" != "0" && "$MSC_DISPLACEMENT" != "1" ]]; then
  echo "Unsupported msc-displacement: ${MSC_DISPLACEMENT}. Expected 0 or 1." >&2
  exit 1
fi
if [[ -n "$MSC_STEP_RANDOM" && "$MSC_STEP_RANDOM" != "0" && "$MSC_STEP_RANDOM" != "1" ]]; then
  echo "Unsupported msc-step-random: ${MSC_STEP_RANDOM}. Expected 0 or 1." >&2
  exit 1
fi
if [[ "$STOP_GRAD_MODE" != "0" && "$STOP_GRAD_MODE" != "1" && "$STOP_GRAD_MODE" != "2" ]]; then
  echo "Unsupported stop-grad-mode: ${STOP_GRAD_MODE}. Expected 0, 1, or 2." >&2
  exit 1
fi
if [[ -n "$SAME_BOUNDARY_STOP" ]] && ! [[ "$SAME_BOUNDARY_STOP" =~ ^[0-9]+$ ]]; then
  echo "Unsupported same-boundary-stop: ${SAME_BOUNDARY_STOP}. Expected non-negative integer." >&2
  exit 1
fi
if [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]] && ! [[ "$SAME_BOUNDARY_MIN_FLIPS" =~ ^[0-9]+$ ]]; then
  echo "Unsupported same-boundary-min-flips: ${SAME_BOUNDARY_MIN_FLIPS}. Expected non-negative integer." >&2
  exit 1
fi
if [[ -n "$SAME_BOUNDARY_FULL_TRACK" && "$SAME_BOUNDARY_FULL_TRACK" != "0" && "$SAME_BOUNDARY_FULL_TRACK" != "1" ]]; then
  echo "Unsupported same-boundary-full-track: ${SAME_BOUNDARY_FULL_TRACK}. Expected 0 or 1." >&2
  exit 1
fi
if [[ -n "$SAME_BOUNDARY_HARD_STOP" ]] && ! [[ "$SAME_BOUNDARY_HARD_STOP" =~ ^[0-9]+$ ]]; then
  echo "Unsupported same-boundary-hard-stop: ${SAME_BOUNDARY_HARD_STOP}. Expected non-negative integer." >&2
  exit 1
fi
if [[ -n "$ROTATE_UP_FLOOR" ]] && ! awk -v v="$ROTATE_UP_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported rotate-up-floor: ${ROTATE_UP_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$CONVERSION_REG_EPS" ]] && ! awk -v v="$CONVERSION_REG_EPS" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported conversion-reg-eps: ${CONVERSION_REG_EPS}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$UMSC_COS_DEN_FLOOR" ]] && ! awk -v v="$UMSC_COS_DEN_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported umsc-cos-den-floor: ${UMSC_COS_DEN_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$UMSC_TAU_BLEND_EPS" ]] && ! awk -v v="$UMSC_TAU_BLEND_EPS" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported umsc-tau-blend-eps: ${UMSC_TAU_BLEND_EPS}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]] && ! awk -v v="$UMSC_SIMPLE_DEN_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported umsc-simple-den-floor: ${UMSC_SIMPLE_DEN_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$UMSC_DISP_RAD_FLOOR" ]] && ! awk -v v="$UMSC_DISP_RAD_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported umsc-disp-rad-floor: ${UMSC_DISP_RAD_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]] && ! awk -v v="$GAMMA_NUMIA_MFP_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported gamma-numia-mfp-floor: ${GAMMA_NUMIA_MFP_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$GAMMA_MFP_CAP" ]] && ! awk -v v="$GAMMA_MFP_CAP" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported gamma-mfp-cap: ${GAMMA_MFP_CAP}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$GAMMA_PE_EKIN_FLOOR" ]] && ! awk -v v="$GAMMA_PE_EKIN_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported gamma-pe-ekin-floor: ${GAMMA_PE_EKIN_FLOOR}. Expected non-negative number." >&2
  exit 1
fi
if [[ -n "$BOX_DIR_DEN_FLOOR" ]] && ! awk -v v="$BOX_DIR_DEN_FLOOR" 'BEGIN{exit !(v+0>=0)}'; then
  echo "Unsupported box-dir-den-floor: ${BOX_DIR_DEN_FLOOR}. Expected non-negative number." >&2
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
RUN_LABEL="${RUN_LABEL}_gst${GRAZING_STOP_TRACK}"
if [[ -n "$BACKWARD_BOUNDARY_STOP" ]]; then
  RUN_LABEL="${RUN_LABEL}_bbs${BACKWARD_BOUNDARY_STOP}"
fi
if [[ -n "$FULL_SANITIZE_STOPGRAD" && "$FULL_SANITIZE_STOPGRAD" != "1" ]]; then
  RUN_LABEL="${RUN_LABEL}_fss${FULL_SANITIZE_STOPGRAD}"
fi
RUN_LABEL="${RUN_LABEL}_x${STOP_GRAD_MODE}"
if [[ -n "$MSC_DISPLACEMENT" ]]; then
  RUN_LABEL="${RUN_LABEL}_md${MSC_DISPLACEMENT}"
fi
if [[ -n "$MSC_STEP_RANDOM" ]]; then
  RUN_LABEL="${RUN_LABEL}_msr${MSC_STEP_RANDOM}"
fi
if [[ -n "$BOUNDARY_TOLERANCE" ]]; then
  BT_TAG=${BOUNDARY_TOLERANCE//./p}
  RUN_LABEL="${RUN_LABEL}_bt${BT_TAG}"
fi
if [[ -n "$MSC_DISP_SAFE_FLOOR" ]]; then
  BSF_TAG=${MSC_DISP_SAFE_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_msf${BSF_TAG}"
fi
if [[ -n "$SAME_BOUNDARY_STOP" ]]; then
  RUN_LABEL="${RUN_LABEL}_sbs${SAME_BOUNDARY_STOP}"
fi
if [[ -n "$SAME_BOUNDARY_POS_TOL" ]]; then
  SBST_TAG=${SAME_BOUNDARY_POS_TOL//./p}
  RUN_LABEL="${RUN_LABEL}_sbt${SBST_TAG}"
fi
if [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]]; then
  RUN_LABEL="${RUN_LABEL}_sbf${SAME_BOUNDARY_MIN_FLIPS}"
fi
if [[ -n "$SAME_BOUNDARY_FULL_TRACK" ]]; then
  RUN_LABEL="${RUN_LABEL}_sbft${SAME_BOUNDARY_FULL_TRACK}"
fi
if [[ -n "$SAME_BOUNDARY_HARD_STOP" ]]; then
  RUN_LABEL="${RUN_LABEL}_sbh${SAME_BOUNDARY_HARD_STOP}"
fi
if [[ -n "$NUMIA_MFP_FLOOR" ]]; then
  NMF_TAG=${NUMIA_MFP_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_nmf${NMF_TAG}"
fi
if [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]]; then
  GNMF_TAG=${GAMMA_NUMIA_MFP_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_gnmf${GNMF_TAG}"
fi
if [[ -n "$GAMMA_MFP_CAP" ]]; then
  GMC_TAG=${GAMMA_MFP_CAP//./p}
  RUN_LABEL="${RUN_LABEL}_gmc${GMC_TAG}"
fi
if [[ -n "$GAMMA_PE_EKIN_FLOOR" ]]; then
  GPEF_TAG=${GAMMA_PE_EKIN_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_gpef${GPEF_TAG}"
fi
if [[ -n "$BOX_DIR_DEN_FLOOR" ]]; then
  BDF_TAG=${BOX_DIR_DEN_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_bdf${BDF_TAG}"
fi
if [[ -n "$ROTATE_UP_FLOOR" ]]; then
  RUF_TAG=${ROTATE_UP_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_ruf${RUF_TAG}"
fi
if [[ -n "$CONVERSION_REG_EPS" ]]; then
  CRE_TAG=${CONVERSION_REG_EPS//./p}
  RUN_LABEL="${RUN_LABEL}_cre${CRE_TAG}"
fi
if [[ -n "$UMSC_COS_DEN_FLOOR" ]]; then
  UCF_TAG=${UMSC_COS_DEN_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_ucf${UCF_TAG}"
fi
if [[ -n "$UMSC_TAU_BLEND_EPS" ]]; then
  UTE_TAG=${UMSC_TAU_BLEND_EPS//./p}
  RUN_LABEL="${RUN_LABEL}_ute${UTE_TAG}"
fi
if [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]]; then
  USF_TAG=${UMSC_SIMPLE_DEN_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_usf${USF_TAG}"
fi
if [[ -n "$UMSC_DISP_RAD_FLOOR" ]]; then
  UDF_TAG=${UMSC_DISP_RAD_FLOOR//./p}
  RUN_LABEL="${RUN_LABEL}_udf${UDF_TAG}"
fi

if [[ -n "$SUFFIX" ]]; then
  RUN_LABEL="${RUN_LABEL}_${SUFFIX}"
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
      EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=1,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB},GRAZING_STOP_TRACK=${GRAZING_STOP_TRACK},STOP_GRAD_MODE=${STOP_GRAD_MODE}"
      [[ -n "$BACKWARD_BOUNDARY_STOP" ]] && EXPORTS+=",BACKWARD_BOUNDARY_STOP=${BACKWARD_BOUNDARY_STOP}"
      [[ -n "$FULL_SANITIZE_STOPGRAD" ]] && EXPORTS+=",FULL_SANITIZE_STOPGRAD=${FULL_SANITIZE_STOPGRAD}"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      [[ -n "$MSC_DISPLACEMENT" ]] && EXPORTS+=",MSC_DISPLACEMENT=${MSC_DISPLACEMENT}"
      [[ -n "$MSC_STEP_RANDOM" ]] && EXPORTS+=",MSC_STEP_RANDOM=${MSC_STEP_RANDOM}"
      [[ -n "$BOUNDARY_TOLERANCE" ]] && EXPORTS+=",BOUNDARY_TOLERANCE=${BOUNDARY_TOLERANCE}"
      [[ -n "$MSC_DISP_SAFE_FLOOR" ]] && EXPORTS+=",MSC_DISP_SAFE_FLOOR=${MSC_DISP_SAFE_FLOOR}"
      [[ -n "$SAME_BOUNDARY_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_STOP=${SAME_BOUNDARY_STOP}"
      [[ -n "$SAME_BOUNDARY_POS_TOL" ]] && EXPORTS+=",SAME_BOUNDARY_POS_TOL=${SAME_BOUNDARY_POS_TOL}"
      [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]] && EXPORTS+=",SAME_BOUNDARY_MIN_FLIPS=${SAME_BOUNDARY_MIN_FLIPS}"
      [[ -n "$SAME_BOUNDARY_FULL_TRACK" ]] && EXPORTS+=",SAME_BOUNDARY_FULL_TRACK=${SAME_BOUNDARY_FULL_TRACK}"
      [[ -n "$SAME_BOUNDARY_HARD_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_HARD_STOP=${SAME_BOUNDARY_HARD_STOP}"
      [[ -n "$NUMIA_MFP_FLOOR" ]] && EXPORTS+=",NUMIA_MFP_FLOOR=${NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]] && EXPORTS+=",GAMMA_NUMIA_MFP_FLOOR=${GAMMA_NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_MFP_CAP" ]] && EXPORTS+=",GAMMA_MFP_CAP=${GAMMA_MFP_CAP}"
      [[ -n "$GAMMA_PE_EKIN_FLOOR" ]] && EXPORTS+=",GAMMA_PE_EKIN_FLOOR=${GAMMA_PE_EKIN_FLOOR}"
      [[ -n "$BOX_DIR_DEN_FLOOR" ]] && EXPORTS+=",BOX_DIR_DEN_FLOOR=${BOX_DIR_DEN_FLOOR}"
      [[ -n "$ROTATE_UP_FLOOR" ]] && EXPORTS+=",ROTATE_UP_FLOOR=${ROTATE_UP_FLOOR}"
      [[ -n "$CONVERSION_REG_EPS" ]] && EXPORTS+=",CONVERSION_REG_EPS=${CONVERSION_REG_EPS}"
      [[ -n "$UMSC_COS_DEN_FLOOR" ]] && EXPORTS+=",UMSC_COS_DEN_FLOOR=${UMSC_COS_DEN_FLOOR}"
      [[ -n "$UMSC_TAU_BLEND_EPS" ]] && EXPORTS+=",UMSC_TAU_BLEND_EPS=${UMSC_TAU_BLEND_EPS}"
      [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]] && EXPORTS+=",UMSC_SIMPLE_DEN_FLOOR=${UMSC_SIMPLE_DEN_FLOOR}"
      [[ -n "$UMSC_DISP_RAD_FLOOR" ]] && EXPORTS+=",UMSC_DISP_RAD_FLOOR=${UMSC_DISP_RAD_FLOOR}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  else
    FILE_PLUS="$OUTDIR/edeps_${SEED}_plus"
    FILE_MINUS="$OUTDIR/edeps_${SEED}_minus"
    if [[ ! -f "$FILE_PLUS" ]]; then
      if [[ "$DERIV_TARGET" == "energy" ]]; then
        echo "Submitting finite-diff (+epsilon) job for seed $SEED (E=${E_PLUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=0,OUTPUT_SUFFIX=plus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${E_PLUS},EVENTS_PER_JOB=${EVENTS_PER_JOB},GRAZING_STOP_TRACK=${GRAZING_STOP_TRACK},STOP_GRAD_MODE=${STOP_GRAD_MODE}"
      else
        echo "Submitting finite-diff (+epsilon) job for seed $SEED (a=${A_PLUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_PLUS},USE_AD=0,OUTPUT_SUFFIX=plus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB},GRAZING_STOP_TRACK=${GRAZING_STOP_TRACK},STOP_GRAD_MODE=${STOP_GRAD_MODE}"
      fi
      [[ -n "$BACKWARD_BOUNDARY_STOP" ]] && EXPORTS+=",BACKWARD_BOUNDARY_STOP=${BACKWARD_BOUNDARY_STOP}"
      [[ -n "$FULL_SANITIZE_STOPGRAD" ]] && EXPORTS+=",FULL_SANITIZE_STOPGRAD=${FULL_SANITIZE_STOPGRAD}"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      [[ -n "$MSC_DISPLACEMENT" ]] && EXPORTS+=",MSC_DISPLACEMENT=${MSC_DISPLACEMENT}"
      [[ -n "$MSC_STEP_RANDOM" ]] && EXPORTS+=",MSC_STEP_RANDOM=${MSC_STEP_RANDOM}"
      [[ -n "$BOUNDARY_TOLERANCE" ]] && EXPORTS+=",BOUNDARY_TOLERANCE=${BOUNDARY_TOLERANCE}"
      [[ -n "$MSC_DISP_SAFE_FLOOR" ]] && EXPORTS+=",MSC_DISP_SAFE_FLOOR=${MSC_DISP_SAFE_FLOOR}"
      [[ -n "$SAME_BOUNDARY_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_STOP=${SAME_BOUNDARY_STOP}"
      [[ -n "$SAME_BOUNDARY_POS_TOL" ]] && EXPORTS+=",SAME_BOUNDARY_POS_TOL=${SAME_BOUNDARY_POS_TOL}"
      [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]] && EXPORTS+=",SAME_BOUNDARY_MIN_FLIPS=${SAME_BOUNDARY_MIN_FLIPS}"
      [[ -n "$SAME_BOUNDARY_FULL_TRACK" ]] && EXPORTS+=",SAME_BOUNDARY_FULL_TRACK=${SAME_BOUNDARY_FULL_TRACK}"
      [[ -n "$SAME_BOUNDARY_HARD_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_HARD_STOP=${SAME_BOUNDARY_HARD_STOP}"
      [[ -n "$NUMIA_MFP_FLOOR" ]] && EXPORTS+=",NUMIA_MFP_FLOOR=${NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]] && EXPORTS+=",GAMMA_NUMIA_MFP_FLOOR=${GAMMA_NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_MFP_CAP" ]] && EXPORTS+=",GAMMA_MFP_CAP=${GAMMA_MFP_CAP}"
      [[ -n "$GAMMA_PE_EKIN_FLOOR" ]] && EXPORTS+=",GAMMA_PE_EKIN_FLOOR=${GAMMA_PE_EKIN_FLOOR}"
      [[ -n "$BOX_DIR_DEN_FLOOR" ]] && EXPORTS+=",BOX_DIR_DEN_FLOOR=${BOX_DIR_DEN_FLOOR}"
      [[ -n "$ROTATE_UP_FLOOR" ]] && EXPORTS+=",ROTATE_UP_FLOOR=${ROTATE_UP_FLOOR}"
      [[ -n "$CONVERSION_REG_EPS" ]] && EXPORTS+=",CONVERSION_REG_EPS=${CONVERSION_REG_EPS}"
      [[ -n "$UMSC_COS_DEN_FLOOR" ]] && EXPORTS+=",UMSC_COS_DEN_FLOOR=${UMSC_COS_DEN_FLOOR}"
      [[ -n "$UMSC_TAU_BLEND_EPS" ]] && EXPORTS+=",UMSC_TAU_BLEND_EPS=${UMSC_TAU_BLEND_EPS}"
      [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]] && EXPORTS+=",UMSC_SIMPLE_DEN_FLOOR=${UMSC_SIMPLE_DEN_FLOOR}"
      [[ -n "$UMSC_DISP_RAD_FLOOR" ]] && EXPORTS+=",UMSC_DISP_RAD_FLOOR=${UMSC_DISP_RAD_FLOOR}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
    if [[ ! -f "$FILE_MINUS" ]]; then
      if [[ "$DERIV_TARGET" == "energy" ]]; then
        echo "Submitting finite-diff (-epsilon) job for seed $SEED (E=${E_MINUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_BASE},USE_AD=0,OUTPUT_SUFFIX=minus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${E_MINUS},EVENTS_PER_JOB=${EVENTS_PER_JOB},GRAZING_STOP_TRACK=${GRAZING_STOP_TRACK},STOP_GRAD_MODE=${STOP_GRAD_MODE}"
      else
        echo "Submitting finite-diff (-epsilon) job for seed $SEED (a=${A_MINUS})"
        EXPORTS="SEED=${SEED},OUTDIR=${OUTDIR},A_VALUE=${A_MINUS},USE_AD=0,OUTPUT_SUFFIX=minus,DERIV_TARGET=${DERIV_TARGET},ENERGY_VALUE=${ENERGY_BASE},EVENTS_PER_JOB=${EVENTS_PER_JOB},GRAZING_STOP_TRACK=${GRAZING_STOP_TRACK},STOP_GRAD_MODE=${STOP_GRAD_MODE}"
      fi
      [[ -n "$BACKWARD_BOUNDARY_STOP" ]] && EXPORTS+=",BACKWARD_BOUNDARY_STOP=${BACKWARD_BOUNDARY_STOP}"
      [[ -n "$FULL_SANITIZE_STOPGRAD" ]] && EXPORTS+=",FULL_SANITIZE_STOPGRAD=${FULL_SANITIZE_STOPGRAD}"
      [[ -n "$KE_CUT" ]] && EXPORTS+=",KE_CUT=${KE_CUT}"
      [[ -n "$THRESHOLD" ]] && EXPORTS+=",THRESHOLD=${THRESHOLD}"
      [[ -n "$THRESHOLD2" ]] && EXPORTS+=",THRESHOLD2=${THRESHOLD2}"
      [[ -n "$MSC_DISPLACEMENT" ]] && EXPORTS+=",MSC_DISPLACEMENT=${MSC_DISPLACEMENT}"
      [[ -n "$MSC_STEP_RANDOM" ]] && EXPORTS+=",MSC_STEP_RANDOM=${MSC_STEP_RANDOM}"
      [[ -n "$BOUNDARY_TOLERANCE" ]] && EXPORTS+=",BOUNDARY_TOLERANCE=${BOUNDARY_TOLERANCE}"
      [[ -n "$MSC_DISP_SAFE_FLOOR" ]] && EXPORTS+=",MSC_DISP_SAFE_FLOOR=${MSC_DISP_SAFE_FLOOR}"
      [[ -n "$SAME_BOUNDARY_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_STOP=${SAME_BOUNDARY_STOP}"
      [[ -n "$SAME_BOUNDARY_POS_TOL" ]] && EXPORTS+=",SAME_BOUNDARY_POS_TOL=${SAME_BOUNDARY_POS_TOL}"
      [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]] && EXPORTS+=",SAME_BOUNDARY_MIN_FLIPS=${SAME_BOUNDARY_MIN_FLIPS}"
      [[ -n "$SAME_BOUNDARY_FULL_TRACK" ]] && EXPORTS+=",SAME_BOUNDARY_FULL_TRACK=${SAME_BOUNDARY_FULL_TRACK}"
      [[ -n "$SAME_BOUNDARY_HARD_STOP" ]] && EXPORTS+=",SAME_BOUNDARY_HARD_STOP=${SAME_BOUNDARY_HARD_STOP}"
      [[ -n "$NUMIA_MFP_FLOOR" ]] && EXPORTS+=",NUMIA_MFP_FLOOR=${NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]] && EXPORTS+=",GAMMA_NUMIA_MFP_FLOOR=${GAMMA_NUMIA_MFP_FLOOR}"
      [[ -n "$GAMMA_MFP_CAP" ]] && EXPORTS+=",GAMMA_MFP_CAP=${GAMMA_MFP_CAP}"
      [[ -n "$GAMMA_PE_EKIN_FLOOR" ]] && EXPORTS+=",GAMMA_PE_EKIN_FLOOR=${GAMMA_PE_EKIN_FLOOR}"
      [[ -n "$BOX_DIR_DEN_FLOOR" ]] && EXPORTS+=",BOX_DIR_DEN_FLOOR=${BOX_DIR_DEN_FLOOR}"
      [[ -n "$ROTATE_UP_FLOOR" ]] && EXPORTS+=",ROTATE_UP_FLOOR=${ROTATE_UP_FLOOR}"
      [[ -n "$CONVERSION_REG_EPS" ]] && EXPORTS+=",CONVERSION_REG_EPS=${CONVERSION_REG_EPS}"
      [[ -n "$UMSC_COS_DEN_FLOOR" ]] && EXPORTS+=",UMSC_COS_DEN_FLOOR=${UMSC_COS_DEN_FLOOR}"
      [[ -n "$UMSC_TAU_BLEND_EPS" ]] && EXPORTS+=",UMSC_TAU_BLEND_EPS=${UMSC_TAU_BLEND_EPS}"
      [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]] && EXPORTS+=",UMSC_SIMPLE_DEN_FLOOR=${UMSC_SIMPLE_DEN_FLOOR}"
      [[ -n "$UMSC_DISP_RAD_FLOOR" ]] && EXPORTS+=",UMSC_DISP_RAD_FLOOR=${UMSC_DISP_RAD_FLOOR}"
      sbatch "${COMMON_SBATCH_ARGS[@]}" --export=${EXPORTS} submit_testem3.slurm
    fi
  fi
done
