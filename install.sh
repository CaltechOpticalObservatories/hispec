#!/usr/bin/env bash

echo "[1/3] Init submodules"
git submodule sync --recursive
git submodule update --init --recursive

echo "[2/3] Update submodules to latest on tracked branches"
git submodule update --remote --merge --recursive || true

echo "[3/3] Create venv and pip install"
PY=${PYTHON:-python3}
VENV_DIR=${VENV_DIR:-.venv}

$PY -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"


if [[ -f "pyproject.toml" ]]; then
  python -m pip install -e ".[dev]" || python -m pip install -e .
elif [[ -f "requirements.txt" ]]; then
  python -m pip install -r requirements.txt
else
  echo "No pyproject.toml or requirements.txt found—nothing to install."
fi

echo "Done."
echo "To activate later: source $VENV_DIR/bin/activate"
