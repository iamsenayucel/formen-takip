export function GroupBadge({ code }: { code: string }) {
  return (
    <span
      className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold tabular-nums tracking-tight"
      style={{ background: "var(--primary-subtle)", color: "var(--primary)", border: "1px solid var(--primary-border)" }}
    >
      {code}
    </span>
  );
}
