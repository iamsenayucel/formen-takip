# Frontend

React + TypeScript + Vite tabanlı istemci uygulaması. Mimari, dizin yapısı,
tema/renk kuralları ve dağıtım detayları için depo kökündeki
[README.md](../README.md#frontend) dosyasına bakın.

## Komutlar

```bash
npm install
npm run dev         # Vite dev sunucusu, :5173 — /api isteklerini :8000'e proxy'ler
npm run build       # tsc -b && vite build
npx tsc --noEmit    # yalnızca tip kontrolü
npm run lint        # oxlint
npm run smoke       # Playwright kritik-yol smoke suite'i (headless)
npm run smoke:headed
npm run smoke:debug
```

## Playwright Smoke Testleri

`scripts/smoke/*.spec.ts` (`@playwright/test`, gerçek assertion'lı, CI-critical
kritik-yol suite'i) ve `scripts/manual/*.mjs` (elle çalıştırılan görsel denetim/
derin senaryo script'leri) olmak üzere iki ayrı kategori vardır; tüm komutlar bu
dizinden (`frontend/`) çalıştırılmalıdır (playwright oradan çözülür). Önkoşullar,
her manuel script'in ne doğruladığı ve eski script'lerin neden temizlendiği için
bkz. depo kökündeki [README.md → Playwright Smoke Testleri](../README.md#playwright-smoke-testleri).

Bir kerelik kurulum: `npx playwright install --with-deps chromium`.
