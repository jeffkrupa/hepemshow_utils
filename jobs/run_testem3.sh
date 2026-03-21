#!/bin/bash
# Arguments: SEED OUTDIR [A_VALUE] [USE_AD] [OUTPUT_SUFFIX] [KE_CUT] [THRESHOLD] [THRESHOLD2] [DERIV_TARGET] [ENERGY_VALUE] [EVENTS_PER_JOB] [GRAZING_STOP_TRACK] [MSC_DISPLACEMENT] [MSC_STEP_RANDOM] [BOUNDARY_TOLERANCE] [MSC_DISP_SAFE_FLOOR] [STOP_GRAD_MODE] [SAME_BOUNDARY_STOP] [SAME_BOUNDARY_POS_TOL] [SAME_BOUNDARY_MIN_FLIPS] [SAME_BOUNDARY_FULL_TRACK] [SAME_BOUNDARY_HARD_STOP] [NUMIA_MFP_FLOOR] [BACKWARD_BOUNDARY_STOP] [FULL_SANITIZE_STOPGRAD] [ROTATE_UP_FLOOR] [CONVERSION_REG_EPS] [UMSC_COS_DEN_FLOOR] [UMSC_TAU_BLEND_EPS] [UMSC_SIMPLE_DEN_FLOOR] [UMSC_DISP_RAD_FLOOR] [GAMMA_NUMIA_MFP_FLOOR] [GAMMA_PE_EKIN_FLOOR] [BOX_DIR_DEN_FLOOR] [GAMMA_MFP_CAP]

SEED=$1
OUTDIR=$2
A_VALUE=${3:-2.3}
USE_AD=${4:-1}
OUTPUT_SUFFIX=${5:-""}
KE_CUT=${6:-""}
THRESHOLD=${7:-""}
THRESHOLD2=${8:-"-1."}
DERIV_TARGET=${9:-"a"}
ENERGY_VALUE=${10:-"10000"}
EVENTS_PER_JOB=${11:-"20000"}
GRAZING_STOP_TRACK=${12:-"1"}
MSC_DISPLACEMENT=${13:-""}
MSC_STEP_RANDOM=${14:-""}
BOUNDARY_TOLERANCE=${15:-""}
MSC_DISP_SAFE_FLOOR=${16:-""}
STOP_GRAD_MODE=${17:-"2"}
SAME_BOUNDARY_STOP=${18:-""}
SAME_BOUNDARY_POS_TOL=${19:-""}
SAME_BOUNDARY_MIN_FLIPS=${20:-""}
SAME_BOUNDARY_FULL_TRACK=${21:-""}
SAME_BOUNDARY_HARD_STOP=${22:-""}
NUMIA_MFP_FLOOR=${23:-""}
BACKWARD_BOUNDARY_STOP=${24:-""}
FULL_SANITIZE_STOPGRAD=${25:-""}
ROTATE_UP_FLOOR=${26:-""}
CONVERSION_REG_EPS=${27:-""}
UMSC_COS_DEN_FLOOR=${28:-""}
UMSC_TAU_BLEND_EPS=${29:-""}
UMSC_SIMPLE_DEN_FLOOR=${30:-""}
UMSC_DISP_RAD_FLOOR=${31:-""}
GAMMA_NUMIA_MFP_FLOOR=${32:-""}
GAMMA_PE_EKIN_FLOOR=${33:-""}
BOX_DIR_DEN_FLOOR=${34:-""}
GAMMA_MFP_CAP=${35:-""}

A_ARG="${A_VALUE}"
E_ARG="${ENERGY_VALUE}"

if [[ "$USE_AD" == "1" ]]; then
    if [[ "$DERIV_TARGET" == "energy" ]]; then
        [[ "$E_ARG" != *:* ]] && E_ARG="${E_ARG}:1"
    else
        [[ "$A_ARG" != *:* ]] && A_ARG="${A_ARG}:1"
    fi
fi

WORKDIR=/sdf/data/atlas/u/jkrupa/hepemshow/hepemshow/build/

cd $WORKDIR || { echo "Directory not found: $WORKDIR"; exit 1; }

# Run the simulation
CMD=(./HepEmShow -n "${EVENTS_PER_JOB}" -s "${SEED}" -a "${A_ARG}" -e "${E_ARG}" --stop-grad-mode "${STOP_GRAD_MODE}" -y "${GRAZING_STOP_TRACK}")
if [[ -n "$THRESHOLD" ]]; then
    CMD+=(-f "${THRESHOLD}")
fi
if [[ -n "$THRESHOLD2" ]]; then
    CMD+=(-k "${THRESHOLD2}")
fi
if [[ -n "$KE_CUT" ]]; then
    CMD+=(-c "${KE_CUT}")
fi
if [[ -n "$MSC_DISPLACEMENT" ]]; then
    CMD+=(-m "${MSC_DISPLACEMENT}")
fi
if [[ -n "$MSC_STEP_RANDOM" ]]; then
    CMD+=(-r "${MSC_STEP_RANDOM}")
fi
if [[ -n "$BOUNDARY_TOLERANCE" ]]; then
    CMD+=(-u "${BOUNDARY_TOLERANCE}")
fi
if [[ -n "$MSC_DISP_SAFE_FLOOR" ]]; then
    CMD+=(-w "${MSC_DISP_SAFE_FLOOR}")
fi
if [[ -n "$SAME_BOUNDARY_STOP" ]]; then
    CMD+=(-q "${SAME_BOUNDARY_STOP}")
fi
if [[ -n "$SAME_BOUNDARY_POS_TOL" ]]; then
    CMD+=(-z "${SAME_BOUNDARY_POS_TOL}")
fi
if [[ -n "$SAME_BOUNDARY_MIN_FLIPS" ]]; then
    CMD+=(-j "${SAME_BOUNDARY_MIN_FLIPS}")
fi
if [[ -n "$SAME_BOUNDARY_FULL_TRACK" ]]; then
    CMD+=(-o "${SAME_BOUNDARY_FULL_TRACK}")
fi
if [[ -n "$SAME_BOUNDARY_HARD_STOP" ]]; then
    CMD+=(-i "${SAME_BOUNDARY_HARD_STOP}")
fi
if [[ -n "$NUMIA_MFP_FLOOR" ]]; then
    CMD+=(-A "${NUMIA_MFP_FLOOR}")
fi
if [[ -n "$GAMMA_NUMIA_MFP_FLOOR" ]]; then
    CMD+=(-T "${GAMMA_NUMIA_MFP_FLOOR}")
fi
if [[ -n "$GAMMA_PE_EKIN_FLOOR" ]]; then
    CMD+=(-U "${GAMMA_PE_EKIN_FLOOR}")
fi
if [[ -n "$BOX_DIR_DEN_FLOOR" ]]; then
    CMD+=(-V "${BOX_DIR_DEN_FLOOR}")
fi
if [[ -n "$ROTATE_UP_FLOOR" ]]; then
    CMD+=(-F "${ROTATE_UP_FLOOR}")
fi
if [[ -n "$CONVERSION_REG_EPS" ]]; then
    CMD+=(-N "${CONVERSION_REG_EPS}")
fi
if [[ -n "$UMSC_COS_DEN_FLOOR" ]]; then
    CMD+=(-P "${UMSC_COS_DEN_FLOOR}")
fi
if [[ -n "$UMSC_TAU_BLEND_EPS" ]]; then
    CMD+=(-Q "${UMSC_TAU_BLEND_EPS}")
fi
if [[ -n "$UMSC_SIMPLE_DEN_FLOOR" ]]; then
    CMD+=(-R "${UMSC_SIMPLE_DEN_FLOOR}")
fi
if [[ -n "$UMSC_DISP_RAD_FLOOR" ]]; then
    CMD+=(-S "${UMSC_DISP_RAD_FLOOR}")
fi
if [[ -n "$GAMMA_MFP_CAP" ]]; then
    CMD+=(-C "${GAMMA_MFP_CAP}")
fi
if [[ -n "$BACKWARD_BOUNDARY_STOP" ]]; then
    CMD+=(-B "${BACKWARD_BOUNDARY_STOP}")
fi
if [[ -n "$FULL_SANITIZE_STOPGRAD" ]]; then
    CMD+=(-G "${FULL_SANITIZE_STOPGRAD}")
fi

echo "Running command: ${CMD[*]}"
echo "Running in directory: $(pwd)"

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
