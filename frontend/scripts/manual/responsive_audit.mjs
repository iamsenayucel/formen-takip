// Kök route'un (dashboard) farklı viewport genişliklerinde yatay taşma (horizontal
// overflow) üretip üretmediğini kontrol eden görsel denetim aracı. CI-critical değildir —
// tasarım/responsive regresyon incelemesi için elle çalıştırılır.
//
// Çalıştırma: npm run smoke:manual:responsive  (frontend/ dizininden)
// Ortam değişkenleri: TARGET_BASE (varsayılan http://localhost:8080), SMOKE_SHOT_DIR,
// SHOT_TAG (ekran görüntüsü dosya adı öneki, varsayılan "baseline"), THEME (light|dark).
import { chromium } from "playwright";
import { resolveBase, resolveShotDir } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();
const TAG = process.env.SHOT_TAG || "baseline";
const THEME = process.env.THEME || "dark";

const widths = [1920, 1536, 1440, 1280, 1100, 1024];

const browser = await chromium.launch();
const errors = [];

for (const width of widths) {
  const page = await browser.newPage({ viewport: { width, height: 1080 } });
  page.on("pageerror", (e) => errors.push(`[${width}] ${String(e)}`));
  page.on("console", (msg) => { if (msg.type() === "error") errors.push(`[${width}] ${msg.text()}`); });

  await page.addInitScript((t) => localStorage.setItem("formen_theme", t), THEME);
  await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${shotDir}/${TAG}-${width}.png`, fullPage: true });
  console.log("saved", TAG, width);

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
  if (scrollWidth > clientWidth + 1) {
    console.log(`  HORIZONTAL OVERFLOW at ${width}: scrollWidth=${scrollWidth} clientWidth=${clientWidth}`);
  }

  await page.close();
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
