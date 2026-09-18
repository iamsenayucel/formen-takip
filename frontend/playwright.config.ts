import { defineConfig, devices } from "@playwright/test";

// Bu suite'in tamamı AUTH_BYPASS=true / VITE_AUTH_BYPASS=true ile çalışan bir stack
// varsayar (yalnızca development/demo — bkz. README "Development Demo Mode"). Gerçek
// Red Hat SSO/Keycloak login akışı gerektiren senaryolar (RBAC, per-role yetki) bilerek
// bu suite'in dışındadır — bkz. frontend/scripts/manual/smoke_test_rbac.mjs.
const BASE = process.env.TARGET_BASE || "http://localhost:8080";

export default defineConfig({
  testDir: "./scripts/smoke",
  timeout: 45_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: BASE,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
