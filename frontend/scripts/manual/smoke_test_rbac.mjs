// RBAC smoke test: 3 rol (Operasyon Yöneticisi/dev-user, Şef/sef-demo, Formen/formen-demo)
// için nav görünürlüğünü, doğrudan URL erişimini (403 sayfası) ve action-level buton
// görünürlüğünü GERÇEK Keycloak login + gerçek backend authorization ile doğrular.
//
// Bu bir CI-critical smoke DEĞİLDİR — manuel/lokal bir doğrulama script'idir, çünkü:
// uygulamanın kendi login formu yoktur (/login her zaman Red Hat SSO/Keycloak'a
// yönlendirir, bkz. src/pages/LoginPage.tsx), bu yüzden AUTH_BYPASS ile çalıştırılamaz
// (bypass tek bir sabit role/kullanıcıya bağlanır — 3 rolü ayrıştıramaz).
//
// Önkoşul:
//   1) Local Keycloak dev stack ayakta olmalı:
//      docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d
//   2) Host makinede `127.0.0.1 keycloak` hosts kaydı olmalı (bkz. README "Yerel
//      Geliştirme: Local Keycloak").
//   3) `docker compose exec backend python -m app.cli seed --seed 42` çalıştırılmış
//      olmalı (dev-user/sef-demo-user/formen-demo-user subject'lerine
//      OPERATIONS_MANAGER/SUPERVISOR/FOREMAN rolleri yalnızca ENVIRONMENT=development'ta
//      otomatik atanır, bkz. backend/app/cli.py::_seed_dev_role_assignments).
//
// Çalıştırma: npm run smoke:manual:rbac  (frontend/ dizininden)
import { chromium } from "playwright";
import { resolveBase, resolveShotDir, trackPageErrors, loginWithKeycloak } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();

const USERS = {
  operationsManager: { username: "dev-user", password: "DevPass123!" },
  supervisor: { username: "sef-demo", password: "DevPass123!" },
  foreman: { username: "formen-demo", password: "DevPass123!" },
};

let failures = 0;

function check(label, condition) {
  const status = condition ? "OK" : "FAIL";
  if (!condition) failures += 1;
  console.log(`[${status}] ${label}`);
}

async function logout(page) {
  const logoutButton = page.getByRole("button", { name: /Çıkış Yap/ });
  if (await logoutButton.isVisible().catch(() => false)) {
    await logoutButton.click();
    await page.waitForTimeout(500);
  }
}

async function navLinkVisible(page, name) {
  return page.getByRole("link", { name }).first().isVisible().catch(() => false);
}

const browser = await chromium.launch();
const page = await browser.newPage();
const { errors } = trackPageErrors(page);

// --- Operasyon Yöneticisi: tüm nav bölümleri görünür ---
await loginWithKeycloak(page, BASE, USERS.operationsManager);
await page.screenshot({ path: `${shotDir}/rbac-1-ops-manager-nav.png` });
check("Ops Yöneticisi: Genel Bakış görünür", await navLinkVisible(page, "Genel Bakış"));
check("Ops Yöneticisi: Tesisler görünür", await navLinkVisible(page, "Tesisler"));
check("Ops Yöneticisi: Tespitler (Operasyonel Zeka) görünür", await navLinkVisible(page, "Tespitler"));
check("Ops Yöneticisi: Operational Impact+ görünür", await navLinkVisible(page, "Operational Impact+"));
check("Ops Yöneticisi: Raporlar (Çıktılar) görünür", await navLinkVisible(page, "Raporlar"));

await page.goto(`${BASE}/reports`, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
check("Ops Yöneticisi: /reports 403 göstermiyor", !(await page.getByText("yetkiniz bulunmamaktadır").isVisible().catch(() => false)));
check("Ops Yöneticisi: 'Rapor Oluştur' butonu görünür", await page.getByRole("button", { name: /Rapor Oluştur/ }).isVisible().catch(() => false));
await page.screenshot({ path: `${shotDir}/rbac-2-ops-manager-reports.png` });
await logout(page);

// --- Şef: Operasyonel Zeka var, Çıktılar yok ---
await loginWithKeycloak(page, BASE, USERS.supervisor);
await page.screenshot({ path: `${shotDir}/rbac-3-supervisor-nav.png` });
check("Şef: Genel Bakış görünür", await navLinkVisible(page, "Genel Bakış"));
check("Şef: Tesisler görünür", await navLinkVisible(page, "Tesisler"));
check("Şef: Tespitler görünür", await navLinkVisible(page, "Tespitler"));
check("Şef: Operational Impact+ görünür", await navLinkVisible(page, "Operational Impact+"));
check("Şef: Raporlar görünmüyor", !(await navLinkVisible(page, "Raporlar")));
check("Şef: Yönetici Özeti görünmüyor", !(await navLinkVisible(page, "Yönetici Özeti")));

await page.goto(`${BASE}/improvement-works`, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
check("Şef: 'Yeni Çalışma Ekle' butonu görünür", await page.getByRole("button", { name: /Yeni Çalışma Ekle/ }).isVisible().catch(() => false));
await page.screenshot({ path: `${shotDir}/rbac-4-supervisor-impact-plus.png` });

await page.goto(`${BASE}/reports`, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
check("Şef: doğrudan /reports URL'i 403 gösteriyor", await page.getByText("yetkiniz bulunmamaktadır").isVisible().catch(() => false));
await page.screenshot({ path: `${shotDir}/rbac-5-supervisor-forbidden.png` });
await logout(page);

// --- Formen: yalnızca Genel Bakış + Performans ---
await loginWithKeycloak(page, BASE, USERS.foreman);
await page.screenshot({ path: `${shotDir}/rbac-6-foreman-nav.png` });
check("Formen: Genel Bakış görünür", await navLinkVisible(page, "Genel Bakış"));
check("Formen: Tesisler görünür", await navLinkVisible(page, "Tesisler"));
check("Formen: Tespitler görünmüyor", !(await navLinkVisible(page, "Tespitler")));
check("Formen: Operational Impact+ görünmüyor", !(await navLinkVisible(page, "Operational Impact+")));
check("Formen: Raporlar görünmüyor", !(await navLinkVisible(page, "Raporlar")));

await page.goto(`${BASE}/anomalies`, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
check("Formen: doğrudan /anomalies URL'i 403 gösteriyor", await page.getByText("yetkiniz bulunmamaktadır").isVisible().catch(() => false));
await page.screenshot({ path: `${shotDir}/rbac-7-foreman-forbidden.png` });
await logout(page);

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
console.log(failures === 0 ? "\nRBAC SMOKE TEST: ALL CHECKS PASSED" : `\nRBAC SMOKE TEST: ${failures} CHECK(S) FAILED`);
await browser.close();
process.exit(failures === 0 ? 0 : 1);
