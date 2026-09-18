import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LoadMoreButton } from "./LoadMoreButton";

describe("LoadMoreButton", () => {
  it("shows loaded/total counts with the default item label", () => {
    render(<LoadMoreButton hasMore={false} isFetchingNextPage={false} onLoadMore={vi.fn()} loadedCount={12} total={40} />);
    expect(screen.getByText("12 / 40 kayıt gösteriliyor")).toBeInTheDocument();
  });

  it("omits the total when it is not known (still-paginating count-unknown case)", () => {
    render(<LoadMoreButton hasMore={true} isFetchingNextPage={false} onLoadMore={vi.fn()} loadedCount={12} total={null} />);
    expect(screen.getByText("12 kayıt gösteriliyor")).toBeInTheDocument();
  });

  it("uses a custom item label when provided", () => {
    render(<LoadMoreButton hasMore={false} isFetchingNextPage={false} onLoadMore={vi.fn()} loadedCount={3} total={3} itemLabel="formen" />);
    expect(screen.getByText("3 / 3 formen gösteriliyor")).toBeInTheDocument();
  });

  it("hides the load-more button when there is no more data", () => {
    render(<LoadMoreButton hasMore={false} isFetchingNextPage={false} onLoadMore={vi.fn()} loadedCount={3} total={3} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows an enabled load-more button when more data is available", () => {
    render(<LoadMoreButton hasMore={true} isFetchingNextPage={false} onLoadMore={vi.fn()} loadedCount={25} total={100} />);
    const button = screen.getByRole("button", { name: "Daha Fazla Yükle" });
    expect(button).toBeEnabled();
  });

  it("calls onLoadMore when clicked", async () => {
    const user = userEvent.setup();
    const onLoadMore = vi.fn();
    render(<LoadMoreButton hasMore={true} isFetchingNextPage={false} onLoadMore={onLoadMore} loadedCount={25} total={100} />);
    await user.click(screen.getByRole("button", { name: "Daha Fazla Yükle" }));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("disables the button and shows a loading label while fetching the next page", () => {
    render(<LoadMoreButton hasMore={true} isFetchingNextPage={true} onLoadMore={vi.fn()} loadedCount={25} total={100} />);
    const button = screen.getByRole("button", { name: "Yükleniyor..." });
    expect(button).toBeDisabled();
  });
});
