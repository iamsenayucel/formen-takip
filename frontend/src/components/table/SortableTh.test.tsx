import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SortableTh } from "./SortableTh";

type Field = "name" | "score";

interface RenderOptions {
  field?: Field;
  activeField?: Field;
  direction?: "asc" | "desc";
}

function renderTh({ field = "name", activeField = "score", direction = "asc" }: RenderOptions = {}) {
  const onSort = vi.fn();
  render(
    <table>
      <thead>
        <tr>
          <SortableTh<Field> field={field} label="Ad" activeField={activeField} direction={direction} onSort={onSort} />
        </tr>
      </thead>
    </table>
  );
  return { onSort };
}

describe("SortableTh", () => {
  it("shows a plain (inactive) sort icon and label when it is not the active column", () => {
    renderTh({ activeField: "score" });
    expect(screen.getByRole("button", { name: "Ad sütununa göre sırala" })).toBeInTheDocument();
  });

  it("announces the current direction in the accessible name when active and ascending", () => {
    renderTh({ activeField: "name", direction: "asc" });
    expect(screen.getByRole("button", { name: "Ad sütununa göre sırala, şu an artan sırada" })).toBeInTheDocument();
  });

  it("announces descending direction when active and descending", () => {
    renderTh({ activeField: "name", direction: "desc" });
    expect(screen.getByRole("button", { name: "Ad sütununa göre sırala, şu an azalan sırada" })).toBeInTheDocument();
  });

  it("calls onSort with its own field when clicked", async () => {
    const user = userEvent.setup();
    const { onSort } = renderTh({ field: "name" });
    await user.click(screen.getByRole("button"));
    expect(onSort).toHaveBeenCalledWith("name");
    expect(onSort).toHaveBeenCalledTimes(1);
  });

  it("calls onSort with its own field even when it is already the active column", async () => {
    const user = userEvent.setup();
    const { onSort } = renderTh({ field: "name", activeField: "name", direction: "asc" });
    await user.click(screen.getByRole("button"));
    expect(onSort).toHaveBeenCalledWith("name");
  });
});
