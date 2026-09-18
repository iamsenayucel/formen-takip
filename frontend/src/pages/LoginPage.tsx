import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, Moon, Sun } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

// Red Hat SSO'ya ulaşılamadığı veya callback hata döndürdüğü durumlarda otomatik
// yönlendirmenin sonsuz döngüye girmesini engeller.
const REDIRECT_GUARD_KEY = "formen_sso_redirect_attempted";

export function LoginPage() {
  const { login, isAuthenticated, isLoading, error } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const attempted = useRef(false);

  const returnTo = (location.state as { from?: string } | null)?.from;

  useEffect(() => {
    if (isAuthenticated) {
      sessionStorage.removeItem(REDIRECT_GUARD_KEY);
      navigate(returnTo || "/", { replace: true });
      return;
    }
    if (isLoading || error || attempted.current) return;
    if (sessionStorage.getItem(REDIRECT_GUARD_KEY)) return;
    attempted.current = true;
    sessionStorage.setItem(REDIRECT_GUARD_KEY, "1");
    void login(returnTo);
  }, [isAuthenticated, isLoading, error, returnTo, login, navigate]);

  const handleManualRetry = () => {
    sessionStorage.removeItem(REDIRECT_GUARD_KEY);
    void login(returnTo);
  };

  return (
    <div className="flex min-h-screen" style={{ background: "var(--page-bg)" }}>
      <button
        onClick={toggleTheme}
        title={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
        aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
        className="fixed right-6 top-6 z-10 flex items-center justify-center rounded-md border p-2 transition-colors hover:bg-[var(--surface-raised)]"
        style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)", background: "var(--surface)" }}
      >
        {theme === "dark" ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
      </button>

      <div
        className="hidden w-[46%] flex-col justify-between p-12 lg:flex"
        style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
      >
        <div />
        <div className="flex flex-col items-center text-center">
          <div className="rounded-lg p-4" style={{ background: "#ffffff" }}>
            <img src="/logo.png" alt="CORVUS Logo" className="w-full max-w-md" />
          </div>
          <h1 className="mt-6 max-w-md text-2xl font-semibold leading-snug" style={{ color: "var(--sidebar-heading)" }}>
            Üretim Performans Yönetim Sistemi
          </h1>
          <p className="mt-3 max-w-sm text-sm" style={{ color: "var(--sidebar-text)" }}>
            50 tesis, 2 vardiya ve 5 temel performans göstergesi üzerinden formen
            performansını tek merkezden izleyin.
          </p>
        </div>
        <p className="text-xs" style={{ color: "var(--sidebar-muted)" }}>Yalnızca yetkilendirilmiş üst yönetim erişimine açıktır.</p>
      </div>

      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex justify-center lg:hidden">
            <div className="rounded-lg p-2" style={{ background: "#ffffff" }}>
              <img src="/logo.png" alt="CORVUS Logo" className="h-auto w-40" />
            </div>
          </div>

          <div className="rounded-lg p-6 text-center" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Sisteme Giriş</h2>
            <p className="mt-1 text-[13px]" style={{ color: "var(--text-muted)" }}>
              Kurumsal Red Hat SSO hesabınızla oturum açmak için yönlendirileceksiniz.
            </p>

            {error && (
              <p className="mt-4 flex items-start gap-1.5 text-left text-xs font-medium" style={{ color: "var(--accent)" }}>
                <AlertCircle size={13} strokeWidth={2} className="mt-0.5 shrink-0" />
                Giriş yapılamadı. SSO servisine ulaşılamıyor olabilir; lütfen daha sonra tekrar deneyin.
              </p>
            )}

            <button
              type="button"
              onClick={handleManualRetry}
              disabled={isLoading}
              className="mt-6 w-full rounded-md py-2 text-sm font-medium text-white transition-colors disabled:opacity-60"
              style={{ background: "var(--accent)" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "var(--accent)")}
            >
              {isLoading ? "Yönlendiriliyor..." : "Red Hat SSO ile Giriş Yap"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
