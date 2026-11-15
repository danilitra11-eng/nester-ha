#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
bashio::log.info "Starting Nestor AI Butler..."
cd /opt/nestor || exit 1
exec python3 -m app.main
