// Tespitler modülünün tool-calling destekli AI analiz ajanını manuel doğrular.
// CI-critical smoke'a bilerek dahil değildir: dış bağımlılık (LLM sağlayıcı) gerektirir
// ve uzun sürer (~90s). AUTH_BYPASS=true / VITE_AUTH_BYPASS=true (dev/demo) ile çalışan
// bir stack + `docker compose exec backend python -m app.cli seed-anomalies --seed 42`
// önkoşuldur.
//
// Çalıştırma: npm run smoke:manual:tool-calling  (frontend/ dizininden)
import { chromium } from "playwright";
import { resolveBase, resolveShotDir, trackPageErrors } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
const { errors } = trackPageErrors(page);

await page.goto(`${BASE}/anomalies`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Toplam Aktif Tespit", { timeout: 15000 });
await page.locator("table tbody tr").nth(2).click();
await page.waitForSelector("text=Sayısal Veriler", { timeout: 10000 });

await page.click('button:has-text("Derinlemesine Analiz")');
await page.waitForTimeout(200);
await page.screenshot({ path: `${shotDir}/tool-calling-mode-selected.png`, fullPage: true });

const analyzeBtn = page.locator('button:has-text("Yapay Zeka ile Analiz Et")');
const refreshBtn = page.locator('button:has-text("Analizi Yenile")');
if (await analyzeBtn.count()) {
  await analyzeBtn.click();
} else {
  await refreshBtn.click();
}

await page.waitForSelector("text=analiz ediliyor", { timeout: 5000 }).catch(() => {});
await page.screenshot({ path: `${shotDir}/tool-calling-analyzing.png`, fullPage: true });
console.log("analyzing state captured");

await page.waitForSelector("text=Yönetici Özeti", { timeout: 90000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/tool-calling-result.png`, fullPage: true });
console.log("tool_calling analysis result rendered");

const stepsToggle = page.locator('button:has-text("adımı göster")');
if (await stepsToggle.count()) {
  await stepsToggle.click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${shotDir}/tool-calling-steps.png`, fullPage: true });
  console.log("tool call steps expanded");
}

console.log("console/page errors:", errors.length ? errors : "none");
await browser.close();
