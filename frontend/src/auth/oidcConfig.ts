import { UserManager, WebStorageStateStore, type UserManagerSettings } from "oidc-client-ts";
import { runtimeConfig } from "../config/runtimeConfig";

const issuerUrl = runtimeConfig.oidcIssuerUrl();
const clientId = runtimeConfig.oidcClientId();

export const oidcConfigStatus = {
  ok: Boolean(issuerUrl) && Boolean(clientId),
  missing: [!issuerUrl && "OIDC_ISSUER_URL", !clientId && "OIDC_CLIENT_ID"].filter((v): v is string => Boolean(v)),
};

const redirectUri = runtimeConfig.oidcRedirectUri() || `${window.location.origin}/auth/callback`;
const postLogoutRedirectUri = runtimeConfig.oidcPostLogoutRedirectUri() || `${window.location.origin}/login`;
const scope = runtimeConfig.oidcScope() || "openid profile email";

export const oidcSettings: UserManagerSettings = {
  authority: issuerUrl,
  client_id: clientId,
  redirect_uri: redirectUri,
  post_logout_redirect_uri: postLogoutRedirectUri,
  response_type: "code",
  scope,
  automaticSilentRenew: true,
  loadUserInfo: false,
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
};

// Tek bir UserManager örneği: hem react-oidc-context'in AuthProvider'ı hem de
// axios API client'ı (bkz. api/client.ts) aynı örneği paylaşır, böylece token
// yönetimi tamamen OIDC client kütüphanesi üzerinden merkezi olarak yürür.
export const userManager = oidcConfigStatus.ok ? new UserManager(oidcSettings) : null;
