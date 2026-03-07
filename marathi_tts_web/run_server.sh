#!/bin/bash

# ── Suppress C++-level CUDA/XLA/absl noise ──────────────────────────────────
# These messages fire from shared libraries at load time, before any Python
# env var can stop them. Redirect ALL stderr through grep for the whole script.
exec 2> >(grep -v -E \
    "cuda_dnn\.cc|cuda_blas\.cc|computation_placer\.cc|\
absl::InitializeLog|WARNING.*written to STDERR|\
Unable to register cu(DNN|BLAS) factory|\
computation placer already registered|\
model of type mt5 to instantiate|tokenizer class you load|\
class this function is called from|MT5Tokenizer|T5Tokenizer|\
^E0000|^W0000|\
Bad request version|over HTTPS, but it only supports HTTP" \
>&2)

# ── Environment variables ────────────────────────────────────────────────────
export DJANGO_DEBUG=True
export CUDA_VISIBLE_DEVICES=-1
export TF_CPP_MIN_LOG_LEVEL=3
export TF_ENABLE_ONEDNN_OPTS=0
export GLOG_minloglevel=3
export ABSL_LOGGING_LOG_TO_STDERR=0
export PYTHONWARNINGS="ignore::RuntimeWarning,ignore::DeprecationWarning,ignore::UserWarning"
export TRANSFORMERS_VERBOSITY=error

# ── Use current virtualenv python ────────────────────────────────────────────
export PYTHON_PATH=$(which python3)
find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf

$PYTHON_PATH manage.py cleanup_temp_files --all --force

# ── Process cleanup trap ─────────────────────────────────────────────────────
MAIN_PID=$$

cleanup() {
    echo "Cleaning up processes..."
    pkill -P $MAIN_PID
    pkill -f "python3 manage.py runserver"
    wait
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ── Database & static files ──────────────────────────────────────────────────
$PYTHON_PATH manage.py migrate --noinput
$PYTHON_PATH manage.py collectstatic --noinput

# ── Start server ─────────────────────────────────────────────────────────────
PORT=${DJANGO_PORT:-8001}
echo ""
echo "Starting server on port $PORT."
echo "  Browser URL: http://localhost:${PORT}/marathi_tts/tts/"
echo ""

# ── Start Django server ──────────────────────────────────────────────────────
# --noreload prevents autoreloader from spawning a second process
$PYTHON_PATH manage.py runserver 127.0.0.1:${PORT} --noreload
