import { useEffect, useRef } from "react";

// Checkbox listesi içeren küçük disclosure popover'lar (MultiSelect, ForemanFilterSelect,
// ForemanMultiSelect) için paylaşılan, düşük riskli erişilebilirlik kalıbı: popover açıkken
// Escape kapatır ve odağı tetikleyici butona geri döndürür. Mevcut tıklama/checkbox
// davranışını veya DOM yapısını değiştirmez — yalnızca eksik klavye çıkışını ekler.
export function useDismissablePopover(open: boolean, onClose: () => void) {
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return triggerRef;
}
