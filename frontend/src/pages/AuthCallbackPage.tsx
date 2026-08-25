import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth as useOidcAuth } from "react-oidc-context";

export function AuthCallbackPage() {
  const oidc = useOidcAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (oidc.isLoading) return;
    if (oidc.isAuthenticated) {
      const state = oidc.user?.state as { returnTo?: string } | undefined;
      navigate(state?.returnTo || "/", { replace: true });
    } else if (oidc.error) {
      navigate("/login", { replace: true });
    }
  }, [oidc.isLoading, oidc.isAuthenticated, oidc.error, oidc.user, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--text-muted)", background: "var(--page-bg)" }}>
      Giriş tamamlanıyor...
    </div>
  );
}
