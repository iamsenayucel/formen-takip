import type { ReactNode } from "react";
import { usePermissions } from "../context/PermissionContext";
import type { Permission } from "../auth/permissions";

interface CanProps {
  permission: Permission;
  children: ReactNode;
}

// Yetkisiz aksiyonları tamamen gizler (disabled değil) — bu, bu projedeki mevcut
// disabled kullanımının (yalnızca async-pending state için) ve nav'ın tamamen gizleme
// davranışının bir devamıdır. Bu yalnızca UX'tir — gerçek yetkilendirme backend'de yapılır.
export function Can({ permission, children }: CanProps) {
  const { can, isLoading } = usePermissions();
  if (isLoading || !can(permission)) return null;
  return <>{children}</>;
}
