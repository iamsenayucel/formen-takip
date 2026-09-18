// Vardiya Analizi sayfası: anomali heatmap'i, hücre drilldown'u (tesis detayına
// yönlendirme) ve Formen–Vardiya Karşılaştırma matrisini light/dark temada doğrular.
// CI-critical smoke'a dahil değildir çünkü çok adımlı, keşfe dayalı bir etkileşim
// zinciridir (heatmap hücre sayısı/veri dağılımı seed'e göre değişir). AUTH_BYPASS=true /
// VITE_AUTH_BYPASS=true (dev/demo) ile çalışan bir stack varsayar.
//
// Çalıştırma: npm run smoke:manual:shift-heatmap  (frontend/ dizininden)
import { chromium } from "playwright";
import { resolveBase, resolveShotDir, trackPageErrors } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1700, height: 1200 } });
const { errors } = trackPageErrors(page);

for (const theme of ["light", "dark"]) {
  await page.addInitScript((t) => localStorage.setItem("formen_theme", t), theme);
  await page.goto(`${BASE}/shift-analysis`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Vardiya Anomali Heatmap", { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${shotDir}/heatmap-page-${theme}.png`, fullPage: true });
  console.log("saved heatmap page", theme);

  const legendNormal = page.locator("text=Normal").first();
  console.log("legend visible:", (await legendNormal.count()) > 0, theme);

  const cellButtons = page.locator("table button");
  const cellCount = await cellButtons.count();
  console.log("heatmap cell button count:", cellCount, theme);

  let navigated = false;
  for (let i = 0; i < Math.min(cellCount, 40) && !navigated; i++) {
    const btn = cellButtons.nth(i);
    const text = (await btn.innerText()).trim();
    if (text === "—") continue;
    await btn.hover();
    await page.waitForTimeout(300);
    const tooltipVisible = await page.locator("text=Durum:").count();
    await btn.click();
    try {
      await page.waitForURL(/\/plants\/.+fs_kpi=/, { timeout: 8000 });
      navigated = true;
      console.log("drilldown navigated, tooltip had 'Durum:':", tooltipVisible > 0, theme);
    } catch {
      await page.goBack().catch(() => {});
    }
  }
  console.log("drilldown navigated:", navigated, theme);

  if (navigated) {
    await page.waitForSelector("text=Formen–Vardiya Karşılaştırması", { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${shotDir}/plant-matrix-${theme}.png`, fullPage: true });
    console.log("saved plant matrix section", theme);

    const matrixCard = page.locator("text=Formen–Vardiya Karşılaştırması").locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]");
    const kpiSelect = matrixCard.locator("select").first();
    const optionCount = await kpiSelect.locator("option").count();
    if (optionCount > 1) {
      await kpiSelect.selectOption({ index: 1 });
      await page.waitForTimeout(1200);
      const selectedLabel = await kpiSelect.locator("option:checked").innerText();
      console.log("changed KPI selector to:", selectedLabel, theme);
    }
    await page.screenshot({ path: `${shotDir}/plant-matrix-kpi-changed-${theme}.png`, fullPage: true });
  }

  await page.evaluate(() => localStorage.clear());
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
