import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useAuthMe } from "../api/hooks";
import { useAuth } from "./AuthContext";
import type { Permission, Role } from "../auth/permissions";

interface PermissionContextValue {
  role: Role | null;
  permissions: Set<Permission>;
  isLoading: boolean;
  can: (permission: Permission) => boolean;
}

const PermissionContext = createContext<PermissionContextValue | undefined>(undefined);

export function PermissionProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { data, isFetched } = useAuthMe(isAuthenticated);

  const value = useMemo<PermissionContextValue>(() => {
    const permissions = new Set((data?.permissions ?? []) as Permission[]);
    return {
      role: (data?.role ?? null) as Role | null,
      permissions,
      // Yalnızca authenticated değilken veya ilk /auth/me yanıtı henüz gelmemişken
      // "loading" say — böylece <Can>/route guard yanlışlıkla erken "yetkisiz" göstermez.
      isLoading: isAuthenticated && !isFetched,
      can: (permission: Permission) => permissions.has(permission),
    };
  }, [data, isAuthenticated, isFetched]);

  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>;
}

export function usePermissions(): PermissionContextValue {
  const ctx = useContext(PermissionContext);
  if (!ctx) throw new Error("usePermissions, PermissionProvider içinde kullanılmalıdır.");
  return ctx;
}
