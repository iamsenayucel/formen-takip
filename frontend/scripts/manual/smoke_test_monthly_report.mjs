// Formen aylık değerlendirme raporu (görüntüleme + PDF indirme) manuel doğrulaması.
// CI-critical smoke'a bilerek dahil değildir: PDF render/indirme akışı, kritik-yol
// navigasyonundan daha pahalı ve daha kırılgandır. AUTH_BYPASS=true / VITE_AUTH_BYPASS=true
// (dev/demo) ile çalışan bir stack varsayar.
//
// Çalıştırma: npm run smoke:manual:monthly-report  (frontend/ dizininden)
// PDF'i görsel olarak doğrulamak için indirilen dosyayı smoke_test_pdf_render.mjs'e
// argüman olarak verin.
import { chromium } from "playwright";
import { resolveBase, resolveShotDir, trackPageErrors } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const { errors } = trackPageErrors(page);

async function shot(name) {
  await page.screenshot({ path: `${shotDir}/${name}.png`, fullPage: true });
  console.log("saved", name);
}

console.log("nav to foremen");
await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

console.log("click first foreman row");
const firstForemanRow = page.locator("table tbody tr").first();
await firstForemanRow.click();
await page.waitForTimeout(1500);

console.log("scroll to monthly reports card");
await page.locator("text=Aylık Değerlendirme Raporları").scrollIntoViewIfNeeded();
await page.waitForTimeout(1500);
await shot("01-foreman-detail-with-monthly-card");

console.log("click Raporu Görüntüle");
const viewButton = page.locator('button:has-text("Raporu Görüntüle")').first();
await viewButton.click();
await page.waitForTimeout(2000);
await shot("02-monthly-report-page");

console.log("checking key sections present");
const bodyText = await page.textContent("body");
const sections = ["Aylık Performans Özeti", "KPI Detayları", "Aylık Değerlendirme"];
for (const s of sections) {
  console.log(`  section "${s}" present:`, bodyText.includes(s));
}

console.log("attempting PDF download");
const [download] = await Promise.all([
  page.waitForEvent("download", { timeout: 15000 }),
  page.click('button:has-text("PDF İndir")'),
]);
const downloadPath = await download.path();
console.log("download saved to (temp):", downloadPath, "suggested filename:", download.suggestedFilename());

console.log("toggle theme (if available) and re-screenshot");
const themeToggle = page.locator('button[aria-label*="tema" i], button[title*="tema" i]').first();
if (await themeToggle.count()) {
  await themeToggle.click();
  await page.waitForTimeout(800);
  await shot("03-monthly-report-page-theme-toggled");
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
