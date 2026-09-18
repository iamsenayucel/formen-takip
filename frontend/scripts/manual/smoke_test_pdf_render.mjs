// Lokal bir PDF dosyasını (ör. smoke_test_monthly_report.mjs'in indirdiği rapor) Chromium
// ile açıp PNG olarak kaydeden görsel doğrulama aracı — Playwright/tarayıcı gerektirmeyen
// bir "PDF içeriği doğru render ediliyor mu" kontrolüdür. CI-critical değildir.
//
// Çalıştırma: node scripts/manual/smoke_test_pdf_render.mjs <pdfPath> [outName.png]
import { chromium } from "playwright";
import { resolveShotDir } from "../smoke_helpers.mjs";

const shotDir = resolveShotDir();
const pdfPath = process.argv[2];
const outName = process.argv[3] ?? "pdf-render.png";

if (!pdfPath) {
  console.error("Kullanım: node scripts/manual/smoke_test_pdf_render.mjs <pdfPath> [outName.png]");
  process.exit(1);
}

const browser = await chromium.launch({ args: ["--enable-features=PdfOopif"] });
const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
await page.goto(`file:///${pdfPath.replace(/\\/g, "/")}`, { waitUntil: "load" });
await page.waitForTimeout(4000);
await page.screenshot({ path: `${shotDir}/${outName}` });
console.log("kaydedildi:", `${shotDir}/${outName}`);
await browser.close();
