#!/usr/bin/env bash
# Boot the Hermes gateway with a self-healing profile.
# - if state/hermes/config.yaml is missing → write fresh cloud profile
# - run gateway in foreground for $RUN_MINUTES
set -u
HERMES="$HOME/.local/bin/hermes"
export HERMES_HOME="${HERMES_HOME:-$PWD/state/hermes}"
mkdir -p "$HERMES_HOME"

# ---- first-boot profile bootstrap ----
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  echo "[boot] no profile found → generating cloud config"
  bash "$(dirname "$0")/bootstrap_profile.sh"
fi

# ---- ALWAYS refresh .env from step env (restored boots skip bootstrap but still need creds) ----
cat > "$HERMES_HOME/.env" << ENV
ROUTER_API_KEY=${ROUTER_API_KEY:-}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS:-}
ENV
chmod 600 "$HERMES_HOME/.env"
echo "[boot] .env refreshed from secrets"

# ---- run ----
echo "[boot] gateway starting (window: ${RUN_MINUTES:-285}m)"
timeout "${RUN_MINUTES:-285}m" "$HERMES" gateway run 2>&1 | tee -a "$HERMES_HOME/gateway.log"
EXIT=$?
echo "[boot] gateway window ended (exit=$EXIT) — exiting cleanly for next cron"
exit 0
