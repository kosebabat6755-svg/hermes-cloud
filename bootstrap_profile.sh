#!/usr/bin/env bash
# Generate a fresh cloud Hermes profile (config.yaml + .env) on first boot.
# Secrets come from GitHub Secrets via workflow env.
set -eu
H="$HERMES_HOME"
mkdir -p "$H"

cat > "$H/config.yaml" << 'YAML'
model:
  provider: custom:9router
  name: Flash-lite

providers:
  9router:
    base_url: https://9router-production-0a47.up.railway.app/v1
    key_env: ROUTER_API_KEY
    default_model: Flash-lite
    models:
      - Flash-lite
      - Chatgem
      - Gem
      - Nvidia-NEM
      - NEM2

memory:
  memory_enabled: true
  memory_char_limit: 20000

display:
  platforms:
    telegram:
      show_reasoning: false
      tool_progress: all
      tool_preview_length: 130

telegram:
  reactions: false
YAML

cat > "$H/.env" << ENV
ROUTER_API_KEY=${ROUTER_API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
ENV
chmod 600 "$H/.env"
echo "[bootstrap] profile written to $H"
