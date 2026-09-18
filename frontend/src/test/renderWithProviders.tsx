import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

interface Options {
  initialEntries?: string[];
  /** Wrap the page under a page-specific provider (e.g. PermissionProvider)
   * on top of the universal QueryClient/Router that every page needs. */
  wrap?: (children: ReactNode) => ReactNode;
}

// Shared across page-integration tests (ReportsPage, PlantsPage,
// AnomaliesPage, ...) so each one only supplies MSW handlers and its own
// page-specific provider needs, not this boilerplate — see CLAUDE.md's
// "actual API client / actual React Query hook / actual Router" guidance.
export function renderWithProviders(ui: ReactElement, options: Options = {}): RenderResult {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });

  function Wrapper({ children }: { children: ReactNode }) {
    const content = options.wrap ? options.wrap(children) : children;
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={options.initialEntries}>{content}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
