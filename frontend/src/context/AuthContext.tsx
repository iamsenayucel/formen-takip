import { createContext, useContext, type ReactNode } from "react";
import { AuthProvider as OidcProvider, useAuth as useOidcAuth } from "react-oidc-context";
import { userManager } from "../auth/oidcConfig";
import { AUTH_BYPASS_ENABLED } from "../auth/authBypass";

interface CurrentUser {
  subject: string;
  fullName: string;
  email: string | null;
}

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: (returnTo?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function Adapter({ children }: { children: ReactNode }) {
  const oidc = useOidcAuth();

  const profile = oidc.user?.profile;
  const user: CurrentUser | null = profile
    ? {
        subject: profile.sub,
        fullName: (profile.name as string | undefined) ?? (profile.preferred_username as string | undefined) ?? profile.sub,
        email: (profile.email as string | undefined) ?? null,
      }
    : null;

  const login = async (returnTo?: string) => {
    await oidc.signinRedirect({ state: { returnTo: returnTo ?? window.location.pathname } });
  };

  const logout = async () => {
    await oidc.signoutRedirect();
  };

  const value: AuthContextValue = {
    user,
    isLoading: oidc.isLoading || oidc.activeNavigator === "signinRedirect",
    isAuthenticated: oidc.isAuthenticated,
    error: oidc.error ? oidc.error.message : null,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

const DEV_BYPASS_USER: CurrentUser = { subject: "dev-demo-user", fullName: "Demo User", email: null };

export function AuthProvider({ children }: { children: ReactNode }) {
  if (AUTH_BYPASS_ENABLED) {
    // Yalnızca geliştirme/demo içindir. Backend AUTH_BYPASS bu kuralı bağımsız olarak
    // uyguladığından geliştirme ortamı dışında etkinleştirilmemelidir.
    const value: AuthContextValue = {
      user: DEV_BYPASS_USER,
      isLoading: false,
      isAuthenticated: true,
      error: null,
      login: async () => {},
      logout: async () => {
        window.location.assign("/");
      },
    };
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  if (!userManager) {
    // OIDC yapılandırması eksik: uygulamayı sessizce çalıştırıp authentication'ı
    // atlamak yerine (fail-open) açıkça engelliyoruz (fail-closed).
    return (
      <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ maxWidth: 480, textAlign: "center", color: "var(--status-negative, #e90128)" }}>
          <h1 className="text-page-title" style={{ marginBottom: 8 }}>SSO yapılandırması eksik</h1>
          <p style={{ fontSize: 13 }}>
            OIDC_ISSUER_URL ve OIDC_CLIENT_ID (runtime config.js veya build-time VITE_*) ayarlanmadan
            uygulama güvenli şekilde başlatılamaz. Lütfen dağıtım yapılandırmasını kontrol edin.
          </p>
        </div>
      </div>
    );
  }

  return (
    <OidcProvider
      userManager={userManager}
      onSigninCallback={() => {
        // oidc-client-ts, code/state query parametrelerini işledikten sonra
        // gerçek hedef route'a yönlendirme AuthCallbackPage tarafından yapılır.
        window.history.replaceState({}, document.title, window.location.pathname);
      }}
    >
      <Adapter>{children}</Adapter>
    </OidcProvider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth, AuthProvider içinde kullanılmalıdır.");
  return ctx;
}
