#!/bin/sh
set -eu

MCP_HOST="${NEXO_COREVIEW_MCP_BIND_HOST:-127.0.0.1}"
MCP_PORT="${NEXO_COREVIEW_MCP_SERVER_PORT:-8001}"
OPENCODE_HOST="${NEXO_COREVIEW_OPENCODE_BIND_HOST:-0.0.0.0}"
OPENCODE_PORT="${NEXO_COREVIEW_OPENCODE_PORT:-4096}"

export NEXO_COREVIEW_MCP_SERVER_URL="${NEXO_COREVIEW_MCP_SERVER_URL:-http://${MCP_HOST}:${MCP_PORT}/sse}"

echo "Starting MCP server on ${MCP_HOST}:${MCP_PORT} (SSE)..."
coreview-agent serve --transport sse --host "${MCP_HOST}" --port "${MCP_PORT}" &
MCP_PID=$!

OPENCODE_PID=""
cleanup() {
  if [ -n "${OPENCODE_PID}" ] && kill -0 "${OPENCODE_PID}" 2>/dev/null; then
    kill "${OPENCODE_PID}" 2>/dev/null || true
    wait "${OPENCODE_PID}" 2>/dev/null || true
  fi
  if kill -0 "${MCP_PID}" 2>/dev/null; then
    kill "${MCP_PID}" 2>/dev/null || true
    wait "${MCP_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

i=0
while [ "$i" -lt 30 ]; do
  if nc -z "${MCP_HOST}" "${MCP_PORT}" 2>/dev/null; then
    break
  fi
  i=$((i + 1))
  sleep 0.2
done

if [ "$#" -eq 0 ]; then
  echo "Starting OpenCode server on ${OPENCODE_HOST}:${OPENCODE_PORT}..."
  exec opencode serve --hostname "${OPENCODE_HOST}" --port "${OPENCODE_PORT}"
fi

echo "Starting OpenCode server on ${OPENCODE_HOST}:${OPENCODE_PORT}..."
opencode serve --hostname "${OPENCODE_HOST}" --port "${OPENCODE_PORT}" &
OPENCODE_PID=$!

i=0
while [ "$i" -lt 120 ]; do
  if wget -q -O /dev/null "http://127.0.0.1:${OPENCODE_PORT}/" 2>/dev/null; then
    break
  fi
  i=$((i + 1))
  sleep 0.5
done

echo "Running: $*"
"$@"
exit $?
