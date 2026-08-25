// Image'ı yeniden build etmeden değişebilmesi gereken deployment değerlerini okur.
// Docker image içinde /config.js, container başlarken environment variable'lardan
// üretilir ve bundle çalışmadan önce window.__APP_CONFIG__ değerini ayarlar.
// `npm run dev` bu dosyayı sunmaz; her anahtar Vite build-time
// import.meta.env.VITE_* değerine fallback yapar ve local geliştirme etkilenmez.
interface RuntimeAppConfig {
  OIDC_ISSUER_URL?: string;
  OIDC_CLIENT_ID?: string;
  OIDC_REDIRECT_URI?: string;
  OIDC_POST_LOGOUT_REDIRECT_URI?: string;
  OIDC_SCOPE?: string;
  AUTH_BYPASS?: string;
}

declare global {
  interface Window {
    __APP_CONFIG__?: RuntimeAppConfig;
  }
}

function readRuntimeConfig<K extends keyof RuntimeAppConfig>(
  runtimeKey: K,
  viteKey: keyof ImportMetaEnv
): string {
  const runtimeValue = window.__APP_CONFIG__?.[runtimeKey]?.trim();
  if (runtimeValue) return runtimeValue;
  return (import.meta.env[viteKey] as string | undefined)?.trim() ?? "";
}

export const runtimeConfig = {
  oidcIssuerUrl: () => readRuntimeConfig("OIDC_ISSUER_URL", "VITE_OIDC_ISSUER_URL"),
  oidcClientId: () => readRuntimeConfig("OIDC_CLIENT_ID", "VITE_OIDC_CLIENT_ID"),
  oidcRedirectUri: () => readRuntimeConfig("OIDC_REDIRECT_URI", "VITE_OIDC_REDIRECT_URI"),
  oidcPostLogoutRedirectUri: () => readRuntimeConfig("OIDC_POST_LOGOUT_REDIRECT_URI", "VITE_OIDC_POST_LOGOUT_REDIRECT_URI"),
  oidcScope: () => readRuntimeConfig("OIDC_SCOPE", "VITE_OIDC_SCOPE"),
  authBypassEnabled: () => readRuntimeConfig("AUTH_BYPASS", "VITE_AUTH_BYPASS") === "true",
};
