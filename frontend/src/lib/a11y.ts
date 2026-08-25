import type { KeyboardEvent, MouseEvent } from "react";

// Tıklanabilir `<tr>` satırları için klavye erişilebilirliği — Tesisler/Gruplar/
// Formenler/Tespitler listelerinde ve ContributionWorkTable'da paylaşılır.
// `guardNestedInteractive: true`, satır içinde kendi onClick'i olan bir buton/link
// varsa (ör. "Kaldır") o öğeye odaklanmışken Enter/Space'in satırı da tetiklemesini
// önler (keydown, native click'ten önce bubble eder).
export function clickableRowProps(
  onActivate: () => void,
  label: string,
  { guardNestedInteractive = false }: { guardNestedInteractive?: boolean } = {}
) {
  return {
    tabIndex: 0,
    role: "button" as const,
    "aria-label": label,
    onClick: onActivate,
    onKeyDown: (e: KeyboardEvent<HTMLTableRowElement>) => {
      if (guardNestedInteractive && e.target !== e.currentTarget) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onActivate();
      }
    },
  };
}

export function stopRowClick(handler: (e: MouseEvent) => void) {
  return (e: MouseEvent) => {
    e.stopPropagation();
    handler(e);
  };
}
