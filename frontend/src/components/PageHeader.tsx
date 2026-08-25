import type { ReactNode } from "react";

export function PageHeader({
  title,
  meta,
  actions,
}: {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <h1 className="text-page-title min-w-0" style={{ color: "var(--text-primary)" }}>
        {title}
      </h1>
      {(meta || actions) && (
        <div className="flex shrink-0 flex-wrap items-center gap-3">
          {meta && (
            <span className="text-body" style={{ color: "var(--text-muted)" }}>
              {meta}
            </span>
          )}
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
    </div>
  );
}
