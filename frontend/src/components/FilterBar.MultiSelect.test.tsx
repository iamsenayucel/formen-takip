import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MultiSelect, type MultiSelectOption } from "./FilterBar";

const OPTIONS: MultiSelectOption[] = [
  { id: "p1", name: "1. Tesis" },
  { id: "p2", name: "2. Tesis" },
];

describe("MultiSelect", () => {
  it("is closed by default and shows the label with no count badge", () => {
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Tesis" })).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows a selected-count badge in the trigger label", () => {
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={["p1"]} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Tesis(1)" })).toBeInTheDocument();
  });

  it("opens the option list on trigger click", async () => {
    const user = userEvent.setup();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    expect(screen.getByText("1. Tesis")).toBeInTheDocument();
    expect(screen.getByText("2. Tesis")).toBeInTheDocument();
  });

  it("calls onChange with the option added when an unselected checkbox is checked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    await user.click(screen.getByText("1. Tesis"));
    expect(onChange).toHaveBeenCalledWith(["p1"]);
  });

  it("calls onChange with the option removed when an already-selected checkbox is unchecked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={["p1", "p2"]} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Tesis(2)" }));
    await user.click(screen.getByText("1. Tesis"));
    expect(onChange).toHaveBeenCalledWith(["p2"]);
  });

  it("does not render a search input below the search threshold (10 options)", async () => {
    const user = userEvent.setup();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    expect(screen.queryByPlaceholderText("Ara...")).not.toBeInTheDocument();
  });

  it("renders a search input once options exceed the search threshold, and filters by it", async () => {
    const user = userEvent.setup();
    const manyOptions: MultiSelectOption[] = Array.from({ length: 12 }, (_, i) => ({
      id: `p${i}`,
      name: `${i}. Tesis`,
    }));
    render(<MultiSelect label="Tesis" options={manyOptions} selected={[]} onChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    const search = screen.getByPlaceholderText("Ara...");
    expect(search).toBeInTheDocument();
    await user.type(search, "5.");
    expect(screen.getByText("5. Tesis")).toBeInTheDocument();
    expect(screen.queryByText("1. Tesis")).not.toBeInTheDocument();
  });

  it("shows a 'no options' message when the options list itself is empty", async () => {
    const user = userEvent.setup();
    render(<MultiSelect label="Tesis" options={[]} selected={[]} onChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    expect(screen.getByText("Seçenek yok")).toBeInTheDocument();
  });

  it("shows a distinct 'no matches' message when a search yields nothing, vs. an empty options list", async () => {
    const user = userEvent.setup();
    const manyOptions: MultiSelectOption[] = Array.from({ length: 12 }, (_, i) => ({
      id: `p${i}`,
      name: `${i}. Tesis`,
    }));
    render(<MultiSelect label="Tesis" options={manyOptions} selected={[]} onChange={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    await user.type(screen.getByPlaceholderText("Ara..."), "no-such-plant");
    expect(screen.getByText("Eşleşen sonuç yok")).toBeInTheDocument();
  });

  it("is disabled and does not open when disabled=true", async () => {
    const user = userEvent.setup();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={vi.fn()} disabled />);
    const trigger = screen.getByRole("button", { name: "Tesis" });
    expect(trigger).toBeDisabled();
    await user.click(trigger);
    expect(screen.queryByText("1. Tesis")).not.toBeInTheDocument();
  });

  it("closes the popover on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<MultiSelect label="Tesis" options={OPTIONS} selected={[]} onChange={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Tesis" });
    await user.click(trigger);
    expect(screen.getByText("1. Tesis")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByText("1. Tesis")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
