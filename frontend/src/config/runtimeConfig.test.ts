import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { runtimeConfig } from "./runtimeConfig";

describe("runtimeConfig", () => {
  beforeEach(() => {
    delete window.__APP_CONFIG__;
  });

  afterEach(() => {
    delete window.__APP_CONFIG__;
    vi.unstubAllEnvs();
  });

  it("reads from window.__APP_CONFIG__ (runtime config.js) when present", () => {
    window.__APP_CONFIG__ = { OIDC_ISSUER_URL: "https://runtime.example.com" };
    expect(runtimeConfig.oidcIssuerUrl()).toBe("https://runtime.example.com");
  });

  it("falls back to the build-time VITE_* value when runtime config is absent", () => {
    vi.stubEnv("VITE_OIDC_ISSUER_URL", "https://buildtime.example.com");
    expect(runtimeConfig.oidcIssuerUrl()).toBe("https://buildtime.example.com");
  });

  it("prefers the runtime value over the build-time value when both are set", () => {
    vi.stubEnv("VITE_OIDC_ISSUER_URL", "https://buildtime.example.com");
    window.__APP_CONFIG__ = { OIDC_ISSUER_URL: "https://runtime.example.com" };
    expect(runtimeConfig.oidcIssuerUrl()).toBe("https://runtime.example.com");
  });

  it("falls back past a blank/whitespace-only runtime value", () => {
    window.__APP_CONFIG__ = { OIDC_ISSUER_URL: "   " };
    vi.stubEnv("VITE_OIDC_ISSUER_URL", "https://buildtime.example.com");
    expect(runtimeConfig.oidcIssuerUrl()).toBe("https://buildtime.example.com");
  });

  it("trims surrounding whitespace from a runtime value", () => {
    window.__APP_CONFIG__ = { OIDC_ISSUER_URL: "  https://runtime.example.com  " };
    expect(runtimeConfig.oidcIssuerUrl()).toBe("https://runtime.example.com");
  });

  it("returns an empty string when neither runtime nor build-time value is set", () => {
    vi.stubEnv("VITE_OIDC_ISSUER_URL", "");
    expect(runtimeConfig.oidcIssuerUrl()).toBe("");
  });

  it("treats AUTH_BYPASS as enabled only for the exact string 'true'", () => {
    window.__APP_CONFIG__ = { AUTH_BYPASS: "true" };
    expect(runtimeConfig.authBypassEnabled()).toBe(true);

    window.__APP_CONFIG__ = { AUTH_BYPASS: "TRUE" };
    expect(runtimeConfig.authBypassEnabled()).toBe(false);

    window.__APP_CONFIG__ = { AUTH_BYPASS: "1" };
    expect(runtimeConfig.authBypassEnabled()).toBe(false);

    delete window.__APP_CONFIG__;
    expect(runtimeConfig.authBypassEnabled()).toBe(false);
  });
});
