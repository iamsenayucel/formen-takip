FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Non-root Nginx, privileged port yerine 8080'i dinler.
FROM nginxinc/nginx-unprivileged:1.27-alpine
# COPY/chmod sahipliği için geçici olarak root'a dön, sonra yeniden nginx kullan.
USER root
COPY --from=build /app/dist /usr/share/nginx/html
# envsubst yalnız tanımlı değişkenleri işler; varsayılan değer literal token kalmasını önler.
ENV BACKEND_UPSTREAM=http://backend:8000
# Nginx entrypoint, BACKEND_UPSTREAM değerini container başlarken template'e uygular.
COPY default.conf.template /etc/nginx/templates/default.conf.template
# OIDC/auth bypass runtime config, başlangıçta development placeholder'ının üstüne yazılır.
COPY config.js.template /usr/share/nginx/html/config.js.template
COPY 40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh && \
    chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/templates
USER nginx
EXPOSE 8080
