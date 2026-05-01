#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Bandit (Security Audit)..."
bandit -r app/ -x app/__pycache__ --severity-level medium

echo "==> Running Black (Formatting Check)..."
black --check app/ tests/ alembic/

echo "==> Audit passed!"