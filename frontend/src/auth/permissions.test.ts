import { describe, expect, it } from "vitest";
import { ROLE_LABELS_TR, type Role } from "./permissions";

// These three roles and their exact string values must stay in lockstep with
// the single source of truth on the backend (backend/app/core/permissions.py
// Role enum + ROLE_PERMISSIONS) — the frontend deliberately does not compute
// role->permission mappings itself (see permissions.ts header comment), but
// the *set of roles* and their Turkish labels are still owned here.
const EXPECTED_ROLES: Role[] = ["FOREMAN", "SUPERVISOR", "OPERATIONS_MANAGER"];

describe("ROLE_LABELS_TR", () => {
  it("has a Turkish label for every known role, and no extras", () => {
    expect(Object.keys(ROLE_LABELS_TR).sort()).toEqual([...EXPECTED_ROLES].sort());
  });

  it("labels each role with the expected Turkish text", () => {
    expect(ROLE_LABELS_TR.FOREMAN).toBe("Formen");
    expect(ROLE_LABELS_TR.SUPERVISOR).toBe("Şef");
    expect(ROLE_LABELS_TR.OPERATIONS_MANAGER).toBe("Operasyon Yöneticisi");
  });
});
