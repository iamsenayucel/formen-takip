import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { Permission, Role } from "./permissions";

// Drift tripwire for the frontend<->backend permission contract: reads
// permissions.py/enums.py as plain text and regex-matches their stable
// literal shapes (enum members, Permission.NAME refs in frozenset blocks),
// without parsing or executing Python.
//
// Duplicates the ROLE_PERMISSIONS fixture from PermissionContext.test.tsx on
// purpose — that test checks runtime behavior, this one checks the mirror
// hasn't drifted from the backend source of truth; they fail independently.
//
// The sanity assertions below guard against the regexes silently matching
// nothing if permissions.py is ever reformatted.

// vitest.config.ts has no custom `root`, so Vitest's cwd is the frontend/
// package directory (where `npm test` is run from, incl. in CI — see
// frontend-ci.yml `working-directory: frontend`) — one level below the repo root.
const REPO_ROOT = resolve(process.cwd(), "..");
const PERMISSIONS_PY = readFileSync(resolve(REPO_ROOT, "backend/app/core/permissions.py"), "utf-8");
const ENUMS_PY = readFileSync(resolve(REPO_ROOT, "backend/app/models/enums.py"), "utf-8");

function extractEnumMembers(source: string, className: string): Map<string, string> {
  const classStart = source.indexOf(`class ${className}(`);
  if (classStart === -1) throw new Error(`extractEnumMembers: "class ${className}(" not found in source`);
  const nextClassStart = source.indexOf("\nclass ", classStart + 1);
  const body = source.slice(classStart, nextClassStart === -1 ? undefined : nextClassStart);

  const members = new Map<string, string>();
  const memberPattern = /^\s{4}(\w+)\s*=\s*"([^"]+)"/gm;
  for (const match of body.matchAll(memberPattern)) {
    members.set(match[1], match[2]);
  }
  return members;
}

function extractRolePermissions(source: string, permissionValueByConst: Map<string, string>): Map<string, Set<string>> {
  const roleBlockPattern = /Role\.(\w+):\s*frozenset\(\s*\{([^}]*)\}/g;
  const rolePermissions = new Map<string, Set<string>>();
  for (const match of source.matchAll(roleBlockPattern)) {
    const roleName = match[1];
    const body = match[2];
    const permissionConstPattern = /Permission\.(\w+)/g;
    const values = new Set<string>();
    for (const permMatch of body.matchAll(permissionConstPattern)) {
      const constName = permMatch[1];
      const value = permissionValueByConst.get(constName);
      if (!value) throw new Error(`extractRolePermissions: unknown Permission.${constName} referenced under Role.${roleName}`);
      values.add(value);
    }
    rolePermissions.set(roleName, values);
  }
  return rolePermissions;
}

const backendPermissionValueByConst = extractEnumMembers(PERMISSIONS_PY, "Permission");
const backendRoleValueByConst = extractEnumMembers(ENUMS_PY, "Role");
const backendRolePermissions = extractRolePermissions(PERMISSIONS_PY, backendPermissionValueByConst);

// The frontend's own mirror of the contract (auth/permissions.ts + the
// matrix every RBAC-aware component test in this repo assumes).
const FRONTEND_PERMISSIONS: Permission[] = [
  "overview.view",
  "performance.view",
  "operational_intelligence.view",
  "operational_impact.contribute",
  "outputs.view",
  "reports.create",
  "reports.download",
];

const FRONTEND_ROLES: Role[] = ["FOREMAN", "SUPERVISOR", "OPERATIONS_MANAGER"];

const FRONTEND_ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  FOREMAN: ["overview.view", "performance.view"],
  SUPERVISOR: ["overview.view", "performance.view", "operational_intelligence.view", "operational_impact.contribute"],
  OPERATIONS_MANAGER: [
    "overview.view",
    "performance.view",
    "operational_intelligence.view",
    "operational_impact.contribute",
    "outputs.view",
    "reports.create",
    "reports.download",
  ],
};

describe("backend permissions.py extraction sanity", () => {
  it("found a non-empty Permission enum", () => {
    expect(backendPermissionValueByConst.size).toBeGreaterThan(0);
  });

  it("found all 3 known roles in ROLE_PERMISSIONS", () => {
    expect(new Set(backendRolePermissions.keys())).toEqual(new Set(FRONTEND_ROLES));
  });
});

describe("RBAC contract: frontend Permission type vs backend Permission enum", () => {
  it("has the exact same set of permission identifier strings", () => {
    const backendValues = new Set(backendPermissionValueByConst.values());
    expect(backendValues).toEqual(new Set(FRONTEND_PERMISSIONS));
  });
});

describe("RBAC contract: frontend Role type vs backend Role enum", () => {
  it("has the exact same set of role identifier strings", () => {
    const backendValues = new Set(backendRoleValueByConst.values());
    expect(backendValues).toEqual(new Set(FRONTEND_ROLES));
  });
});

describe("RBAC contract: frontend ROLE_PERMISSIONS mirror vs backend ROLE_PERMISSIONS", () => {
  it.each(FRONTEND_ROLES)("role %s grants exactly the same permissions on both sides", (role) => {
    expect(backendRolePermissions.get(role)).toEqual(new Set(FRONTEND_ROLE_PERMISSIONS[role]));
  });
});
