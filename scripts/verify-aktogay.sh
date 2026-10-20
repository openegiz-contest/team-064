#!/usr/bin/env bash
# Verify the running OpenEgiz + Aktogay Compose stack and all six scenarios.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec python3 scripts/verify_aktogay.py
