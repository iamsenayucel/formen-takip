import { test, expect } from "@playwright/test";
import { trackPageErrors } from "../smoke_helpers.mjs";

// Kritik yol: üst yönetimin her oturumda gerçekten açtığı sayfalar. AUTH_BYPASS=true /
// VITE_AUTH_BYPASS=true (yalnızca development/demo) ile çalışan bir stack varsayar — bkz.
// playwright.config.ts. Her route için tek doğrulama: sayfa başlığı (PageHeader -> <h1>)
// görünür, ve ne konsolda ne de /api/v1/ isteklerinde hata var.
const ROUTES: { path: string; heading: string }[] = [
  { path: "/", heading: "Genel Bakış" },
  { path: "/plants", heading: "Tesisler" },
  { path: "/groups", heading: "Gruplar" },
  { path: "/foremen", heading: "Formenler" },
  { path: "/kpis", heading: "KPI Analizi" },
  { path: "/anomalies", heading: "Tespitler" },
  { path: "/shift-analysis", heading: "Vardiya Analizi" },
  { path: "/improvement-works", heading: "Operational Impact+" },
];

for (const { path, heading } of ROUTES) {
  test(`${path} açılır ve ana başlık görünür`, async ({ page }) => {
    const { errors, apiErrors } = trackPageErrors(page);
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    expect(apiErrors, `API hataları: ${apiErrors.join("; ")}`).toEqual([]);
    expect(errors, `Konsol hataları: ${errors.join("; ")}`).toEqual([]);
  });
}

test("sidebar navigasyonu ile Tesisler sayfasına geçilebilir", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
  await page.getByRole("link", { name: "Tesisler" }).click();
  await expect(page).toHaveURL(/\/plants$/);
  await expect(page.getByRole("heading", { level: 1, name: "Tesisler" })).toBeVisible();
});

test("Tesisler listesinden bir tesise girilebilir", async ({ page }) => {
  await page.goto("/plants");
  await expect(page.getByRole("heading", { level: 1, name: "Tesisler" })).toBeVisible();
  const firstRow = page.locator("table tbody tr").first();
  await expect(firstRow).toBeVisible();
  await firstRow.click();
  await expect(page).toHaveURL(/\/plants\/.+/);
});

test("Formenler listesinden bir formene girilebilir", async ({ page }) => {
  await page.goto("/foremen");
  await expect(page.getByRole("heading", { level: 1, name: "Formenler" })).toBeVisible();
  const firstRow = page.locator("table tbody tr").first();
  await expect(firstRow).toBeVisible();
  await firstRow.click();
  await expect(page).toHaveURL(/\/foremen\/.+/);
});
