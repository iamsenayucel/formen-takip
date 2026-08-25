import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function LoadingState({ label = "Yükleniyor..." }: { label?: string }) {
  return (
    <div className="text-body flex items-center justify-center gap-2 py-12" style={{ color: "var(--text-muted)" }}>
      <Loader2 size={15} strokeWidth={2} className="animate-spin" style={{ color: "var(--primary)" }} />
      {label}
    </div>
  );
}

export function ErrorState({ message = "Veri yüklenirken bir hata oluştu." }: { message?: string }) {
  return (
    <div className="text-body flex flex-col items-center justify-center gap-2 py-12 text-center" style={{ color: "var(--status-negative)" }}>
      <AlertTriangle size={20} strokeWidth={1.5} />
      {message}
    </div>
  );
}

export function EmptyState({ message = "Seçilen filtrelerle eşleşen veri bulunamadı." }: { message?: string }) {
  return (
    <div className="text-body flex flex-col items-center justify-center gap-2 py-12 text-center" style={{ color: "var(--text-muted)" }}>
      <Inbox size={20} strokeWidth={1.5} />
      {message}
    </div>
  );
}

export function Card({
  title,
  subtitle,
  children,
  action,
}: {
  title?: string;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="min-w-0 rounded-lg p-[var(--space-card-padding)]"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      {title && (
        <div className="mb-[var(--space-card-header-gap)] flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-section-title" style={{ color: "var(--text-secondary)" }}>
              {title}
            </h3>
            {subtitle && (
              <p className="text-metadata mt-1" style={{ color: "var(--text-muted)" }}>
                {subtitle}
              </p>
            )}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
