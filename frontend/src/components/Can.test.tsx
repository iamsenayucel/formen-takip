import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Can } from "./Can";

const { usePermissionsMock } = vi.hoisted(() => ({ usePermissionsMock: vi.fn() }));
vi.mock("../context/PermissionContext", () => ({ usePermissions: usePermissionsMock }));

function mockPermissions(overrides: { can?: (p: string) => boolean; isLoading?: boolean }) {
  usePermissionsMock.mockReturnValue({
    role: "OPERATIONS_MANAGER",
    permissions: new Set(),
    isLoading: false,
    can: () => false,
    ...overrides,
  });
}

describe("Can", () => {
  it("renders its children when the permission is granted", () => {
    mockPermissions({ can: (p) => p === "reports.create" });
    render(
      <Can permission="reports.create">
        <button>Rapor Oluştur</button>
      </Can>
    );
    expect(screen.getByRole("button", { name: "Rapor Oluştur" })).toBeInTheDocument();
  });

  it("renders nothing when the permission is not granted", () => {
    mockPermissions({ can: () => false });
    const { container } = render(
      <Can permission="reports.create">
        <button>Rapor Oluştur</button>
      </Can>
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing while permissions are still loading, even if can() would return true", () => {
    // isLoading=true must win over an optimistic can() result — otherwise a
    // gated action button could flash visible before the real permission
    // check resolves.
    mockPermissions({ can: () => true, isLoading: true });
    render(
      <Can permission="reports.create">
        <button>Rapor Oluştur</button>
      </Can>
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("does not render an action-permission's children just because a view-permission is granted (page:view != action:create)", () => {
    // Guards against conflating "can see this page" with "can perform this
    // action on it" — the two are separate permission strings in this app
    // (operational_intelligence.view vs operational_impact.contribute,
    // outputs.view vs reports.create/reports.download).
    mockPermissions({ can: (p) => p === "outputs.view" });
    render(
      <Can permission="reports.create">
        <button>Rapor Oluştur</button>
      </Can>
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("evaluates each Can independently when multiple permissions are checked side by side", () => {
    mockPermissions({ can: (p) => p === "reports.download" });
    render(
      <div>
        <Can permission="reports.create">
          <button>Rapor Oluştur</button>
        </Can>
        <Can permission="reports.download">
          <button>İndir</button>
        </Can>
      </div>
    );
    expect(screen.queryByRole("button", { name: "Rapor Oluştur" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "İndir" })).toBeInTheDocument();
  });
});
