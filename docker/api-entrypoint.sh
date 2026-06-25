#!/bin/sh
set -e

# Worker spawns agent containers via the mounted Docker socket (requires root).
case "$1" in
  code-review)
    if [ "$2" = "job" ] && [ "$3" = "worker" ]; then
      exec "$@"
    fi
    ;;
esac

# API: named volumes mount as root; ensure the app user can write OpenCode config.
if [ -d /config ]; then
  chown -R app:app /config 2>/dev/null || true
fi

exec runuser -u app -- "$@"
