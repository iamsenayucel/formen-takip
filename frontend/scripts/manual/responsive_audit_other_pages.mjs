// /plants, /foremen, /kpis sayfalarının 1280px genişlikte yatay taşma üretip
// üretmediğini kontrol eden görsel denetim aracı. CI-critical değildir.
//
// Çalıştırma: npm run smoke:manual:responsive-pages  (frontend/ dizininden)
// Ortam değişkenleri: TARGET_BASE (varsayılan http://localhost:8080), SMOKE_SHOT_DIR,
// THEME (light|dark, varsayılan dark).
import { chromium } from "playwright";
import { resolveBase, resolveShotDir } from "../smoke_helpers.mjs";

const BASE = resolveBase();
const shotDir = resolveShotDir();
const THEME = process.env.THEME || "dark";

const pages = ["/plants", "/foremen", "/kpis"];
const browser = await chromium.launch();
const errors = [];

for (const path of pages) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1080 } });
  page.on("pageerror", (e) => errors.push(`[${path}] ${String(e)}`));
  page.on("console", (msg) => { if (msg.type() === "error") errors.push(`[${path}] ${msg.text()}`); });
  await page.addInitScript((t) => localStorage.setItem("formen_theme", t), THEME);
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1200);
  const name = path.replace(/\//g, "") || "root";
  await page.screenshot({ path: `${shotDir}/page-${name}-1280.png`, fullPage: true });
  console.log("saved", path);
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
  if (scrollWidth > clientWidth + 1) console.log(`  OVERFLOW ${path}: ${scrollWidth} > ${clientWidth}`);
  await page.close();
}

console.log("ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
