#!/bin/sh
set -e

# Named volumes mount as root; ensure the app user can write OpenCode config.
if [ -d /config ]; then
  chown -R app:app /config 2>/dev/null || true
fi

exec runuser -u app -- "$@"
