#!/usr/bin/env bash
set -euo pipefail
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python scripts/install_argos_env.py
