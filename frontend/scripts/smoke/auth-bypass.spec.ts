import { test, expect } from "@playwright/test";
import { trackPageErrors } from "../smoke_helpers.mjs";

// AUTH_BYPASS=true / VITE_AUTH_BYPASS=true (yalnızca development/demo) ile çalışan bir
// stack varsayar. Bu test bypass'ı "onaylı" bir production davranışı olarak doğrulamaz —
// yalnızca dev/demo modunun kendi sözleşmesini (login akışına girmeden dashboard açılır)
// doğrular. Production'da AUTH_BYPASS asla açılamaz (bkz. README "Fail-closed").

test.describe("Auth bypass (dev/demo mode)", () => {
  test("kök route login'e yönlendirmeden doğrudan açılır", async ({ page }) => {
    const { errors } = trackPageErrors(page);
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
    expect(errors, `Konsol hataları: ${errors.join("; ")}`).toEqual([]);
  });

  test("/login doğrudan ziyaret edildiğinde dashboard'a geri döner", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
  });

  test("çıkış yap sonrası hata vermeden kök route'ta kalır", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
    await page.getByRole("button", { name: "Çıkış Yap" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
  });
});
