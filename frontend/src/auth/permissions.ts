// Backend'deki tek doğruluk kaynağıyla (app/core/permissions.py) birebir eşleşen sabitler.
// Permission -> rol eşlemesi burada TUTULMAZ: rol ve izinler her zaman /auth/me'den gelir,
// frontend kendi başına hesaplamaz (bkz. PermissionContext).
export type Permission =
  | "overview.view"
  | "performance.view"
  | "operational_intelligence.view"
  | "operational_impact.contribute"
  | "outputs.view"
  | "reports.create"
  | "reports.download";

export type Role = "FOREMAN" | "SUPERVISOR" | "OPERATIONS_MANAGER";

export const ROLE_LABELS_TR: Record<Role, string> = {
  FOREMAN: "Formen",
  SUPERVISOR: "Şef",
  OPERATIONS_MANAGER: "Operasyon Yöneticisi",
};
