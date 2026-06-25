#!/bin/sh
set -e

cd /workspace/backend
uv sync --locked --all-groups

exec "$@"
