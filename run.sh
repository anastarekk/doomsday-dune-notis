#!/bin/sh
# Runs one check in a throwaway container. Called by cron every 7 minutes.
cd "$(dirname "$0")" || exit 1
[ -f .env ] || { echo "$(date -u) missing .env (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID), skipping"; exit 1; }
mkdir -p data
[ -f data/notified.json ] || cp notified.json data/notified.json
echo "--- $(date -u '+%Y-%m-%d %H:%M:%S') UTC"
docker run --rm --env-file .env -v "$PWD/data:/data" movie-notifier
