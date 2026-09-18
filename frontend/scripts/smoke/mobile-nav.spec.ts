import { test, expect, devices } from "@playwright/test";

// Yönetim, tablet/telefon genişliğinde de bu uygulamayı açabiliyor olmalı — mobil
// hamburger menüsü kritik bir etkileşimdir (bkz. src/components/Layout.tsx).
//
// devices["iPhone 13"] carries defaultBrowserType: "webkit", which overrides
// this suite's single "chromium" project and launches WebKit for this file
// only — a second browser engine this repo doesn't install anywhere
// (playwright.config.ts has one chromium project; the documented CI plan
// installs only chromium too). Pinning defaultBrowserType back to chromium
// keeps the iPhone 13 viewport/UA/touch emulation via Chrome's own mobile
// emulation instead, so this suite never depends on a second browser engine.
test.use({ ...devices["iPhone 13"], defaultBrowserType: "chromium" });

test("mobil menü açılır, sayfa arası gezinir ve kapanır", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();

  const hamburger = page.getByLabel("Menüyü aç");
  await expect(hamburger).toBeVisible();
  await hamburger.click();

  const closeButton = page.getByLabel("Menüyü kapat");
  await expect(closeButton).toBeVisible();

  await page.getByRole("link", { name: "Tesisler" }).last().click();
  await expect(page).toHaveURL(/\/plants$/);
  await expect(closeButton).toBeHidden();
});
