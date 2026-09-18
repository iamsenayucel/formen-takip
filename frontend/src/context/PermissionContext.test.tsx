import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PermissionProvider, usePermissions } from "./PermissionContext";
import type { Permission } from "../auth/permissions";

const { useAuthMeMock } = vi.hoisted(() => ({ useAuthMeMock: vi.fn() }));
const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../api/hooks", () => ({ useAuthMe: useAuthMeMock }));
vi.mock("./AuthContext", () => ({ useAuth: useAuthMock }));

// The real ROLE_PERMISSIONS matrix lives only on the backend
// (backend/app/core/permissions.py) — the frontend always receives the
// resolved permission list from /auth/me rather than computing it itself
// (see auth/permissions.ts header comment). Mirroring that matrix here keeps
// these tests grounded in the actual server-side contract instead of an
// invented one.
const ROLE_PERMISSIONS: Record<string, Permission[]> = {
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

const ALL_PERMISSIONS: Permission[] = [
  "overview.view",
  "performance.view",
  "operational_intelligence.view",
  "operational_impact.contribute",
  "outputs.view",
  "reports.create",
  "reports.download",
];

function Probe() {
  const { role, permissions, isLoading, can } = usePermissions();
  return (
    <div>
      <span data-testid="role">{role ?? "none"}</span>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="permission-count">{permissions.size}</span>
      {ALL_PERMISSIONS.map((p) => (
        <span key={p} data-testid={`can-${p}`}>
          {String(can(p))}
        </span>
      ))}
    </div>
  );
}

interface AuthMeMockResult {
  data?: { subject: string; displayName: string | null; email: string | null; role: string | null; permissions: string[] };
  isFetched: boolean;
}

function renderWithAuth(authMeResult: AuthMeMockResult, isAuthenticated: boolean) {
  useAuthMock.mockReturnValue({ isAuthenticated });
  useAuthMeMock.mockReturnValue(authMeResult);
  return render(
    <PermissionProvider>
      <Probe />
    </PermissionProvider>
  );
}

describe.each(Object.entries(ROLE_PERMISSIONS))("PermissionContext for role %s", (role, granted) => {
  it(`grants exactly the backend-defined permission set for ${role}`, () => {
    renderWithAuth({ data: { subject: "s1", displayName: "Test", email: null, role, permissions: granted }, isFetched: true }, true);
    for (const permission of ALL_PERMISSIONS) {
      expect(screen.getByTestId(`can-${permission}`)).toHaveTextContent(String(granted.includes(permission)));
    }
    expect(screen.getByTestId("role")).toHaveTextContent(role);
  });
});

describe("PermissionContext loading semantics", () => {
  it("is loading while authenticated but /auth/me has not resolved yet", () => {
    renderWithAuth({ data: undefined, isFetched: false }, true);
    expect(screen.getByTestId("loading")).toHaveTextContent("true");
    expect(screen.getByTestId("permission-count")).toHaveTextContent("0");
  });

  it("is not loading once authenticated and /auth/me has resolved", () => {
    renderWithAuth({ data: { subject: "s1", displayName: null, email: null, role: "FOREMAN", permissions: [] }, isFetched: true }, true);
    expect(screen.getByTestId("loading")).toHaveTextContent("false");
  });

  it("is not loading when unauthenticated, even if /auth/me has not fetched (query is disabled)", () => {
    renderWithAuth({ data: undefined, isFetched: false }, false);
    expect(screen.getByTestId("loading")).toHaveTextContent("false");
  });

  it("treats a missing role as null and grants no permissions when unauthenticated", () => {
    renderWithAuth({ data: undefined, isFetched: false }, false);
    expect(screen.getByTestId("role")).toHaveTextContent("none");
    expect(screen.getByTestId("permission-count")).toHaveTextContent("0");
  });

  it("treats an unrecognized/unknown permission string as not granted", () => {
    useAuthMock.mockReturnValue({ isAuthenticated: true });
    useAuthMeMock.mockReturnValue({
      data: { subject: "s1", displayName: null, email: null, role: "FOREMAN", permissions: ["overview.view"] },
      isFetched: true,
    });
    function UnknownProbe() {
      const { can } = usePermissions();
      return <span data-testid="unknown">{String(can("does_not_exist.action" as Permission))}</span>;
    }
    render(
      <PermissionProvider>
        <UnknownProbe />
      </PermissionProvider>
    );
    expect(screen.getByTestId("unknown")).toHaveTextContent("false");
  });
});

describe("usePermissions outside a provider", () => {
  it("throws a descriptive error", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow("usePermissions, PermissionProvider içinde kullanılmalıdır.");
    consoleError.mockRestore();
  });
});
