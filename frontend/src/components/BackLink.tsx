import { ChevronLeft } from "lucide-react";

export function BackLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-fit items-center gap-1 text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40"
      style={{ color: "var(--primary)" }}
    >
      <ChevronLeft size={13} strokeWidth={2} />
      {label}
    </button>
  );
}
