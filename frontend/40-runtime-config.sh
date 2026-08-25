#!/bin/sh
# Nginx başlamadan önce container env'inden config.js üretir.
# Böylece OIDC ayarları image'a gömülmez.
set -eu

TEMPLATE="/usr/share/nginx/html/config.js.template"
OUTPUT="/usr/share/nginx/html/config.js"

if [ -f "$TEMPLATE" ]; then
  envsubst '${VITE_OIDC_ISSUER_URL} ${VITE_OIDC_CLIENT_ID} ${VITE_OIDC_REDIRECT_URI} ${VITE_OIDC_POST_LOGOUT_REDIRECT_URI} ${VITE_OIDC_SCOPE} ${VITE_AUTH_BYPASS}' \
    < "$TEMPLATE" > "$OUTPUT"
fi
