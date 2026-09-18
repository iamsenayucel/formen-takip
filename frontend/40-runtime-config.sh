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

# CSP connect-src'te sadece OIDC issuer origin'i (scheme://host:port) gerekir, tüm
# VITE_OIDC_ISSUER_URL değil (bkz. default.conf.template'deki açıklama — path'li bir
# CSP source, o path'e tam eşleşmeyen alt path isteklerini (token/discovery endpoint'leri)
# engelliyor). envsubst yalnız literal substitution yaptığından origin'i burada
# hesaplayıp 20-envsubst-on-templates.sh'in ürettiği default.conf içindeki placeholder'ı
# nginx başlamadan önce yerine yazıyoruz.
NGINX_CONF="/etc/nginx/conf.d/default.conf"
if [ -f "$NGINX_CONF" ]; then
  if [ -n "${VITE_OIDC_ISSUER_URL:-}" ]; then
    _rest="${VITE_OIDC_ISSUER_URL#*://}"
    _scheme="${VITE_OIDC_ISSUER_URL%%://*}"
    _hostport="${_rest%%/*}"
    OIDC_ISSUER_ORIGIN="${_scheme}://${_hostport}"
  else
    OIDC_ISSUER_ORIGIN=""
  fi
  sed -i "s#__OIDC_ISSUER_ORIGIN__#${OIDC_ISSUER_ORIGIN}#g" "$NGINX_CONF"
fi
