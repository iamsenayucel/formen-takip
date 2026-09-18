import { ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div
        className="flex h-12 w-12 items-center justify-center rounded-full"
        style={{ background: "var(--surface-raised)", color: "var(--accent)" }}
      >
        <ShieldAlert size={22} strokeWidth={1.75} />
      </div>
      <h1 className="mt-4 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
        Bu sayfayı görüntüleme yetkiniz bulunmamaktadır
      </h1>
      <p className="mt-2 max-w-sm text-[13px]" style={{ color: "var(--text-muted)" }}>
        Erişimin gerekli olduğunu düşünüyorsanız sistem yöneticinizle iletişime geçebilirsiniz.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-md border px-4 py-2 text-xs font-medium transition-colors hover:bg-[var(--page-bg)]"
        style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
      >
        Genel Bakış'a dön
      </Link>
    </div>
  );
}
