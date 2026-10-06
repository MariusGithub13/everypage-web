#!/bin/sh
# Rebuild EveryPage with the settings it MUST run with (06.10.2026: a plain `docker compose up` bound 127.0.0.1 and lost the key -> 504).
cd /opt/devaland/everypage-web && EVERYPAGE_ENV_FILE=/opt/devaland/shared/secrets/nebius.env EVERYPAGE_BIND=172.17.0.1:8092 docker compose up -d --build "$@"
