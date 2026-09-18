// Playwright scriptleri (hem otomatik smoke suite hem manuel audit script'leri) için
// paylaşılan yardımcılar. Kişisel makine path'i veya hardcoded base URL barındırmaz —
// her ikisi de ortam değişkeninden okunur (bkz. frontend/README.md "Playwright Smoke").
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPTS_DIR = path.dirname(fileURLToPath(import.meta.url));

export function resolveBase() {
  return process.env.TARGET_BASE || "http://localhost:8080";
}

export function resolveShotDir() {
  const dir = process.env.SMOKE_SHOT_DIR || path.join(SCRIPTS_DIR, ".smoke-output");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// page/pageerror/console-error ve /api/v1/ altındaki 4xx/5xx yanıtlarını tek yerden
// toplar — her script kendi event listener'ını tekrar yazmasın diye.
export function trackPageErrors(page) {
  const errors = [];
  const apiErrors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("response", (res) => {
    if (res.status() >= 400 && res.url().includes("/api/v1/")) {
      apiErrors.push(`${res.status()} ${res.url()}`);
    }
  });
  return { errors, apiErrors };
}

// Yalnızca gerçek per-role yetkilendirmeyi doğrulayan manuel script'ler (ör.
// smoke_test_rbac.mjs) için: uygulamanın kendi login formu YOKTUR (bkz.
// src/pages/LoginPage.tsx) — /login her zaman Red Hat SSO / Keycloak'a
// yönlendirir. Bu yüzden gerçek bir Keycloak login sayfasına karşı çalışır.
//
// Önkoşul: local Keycloak dev stack ayakta olmalı (`docker compose -f docker-compose.yml
// -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d`) ve host makinede
// `127.0.0.1 keycloak` hosts kaydı olmalı (bkz. README "Yerel Geliştirme: Local Keycloak").
// Keycloak'ın varsayılan temasındaki alan id'lerine (#username/#password/#kc-login) bağımlıdır.
export async function loginWithKeycloak(page, base, { username, password }) {
  await page.goto(`${base}/login`);
  await page.waitForURL(/\/protocol\/openid-connect\/auth/, { timeout: 20000 });
  await page.fill("#username", username);
  await page.fill("#password", password);
  await page.click("#kc-login");
  await page.waitForURL(`${base}/`, { timeout: 20000 });
}
