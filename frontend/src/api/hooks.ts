import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  AnalysisMode,
  AuthMeResponse,
  AnomalyDetail,
  AnomalyInvestigation,
  AnomalyListItem,
  AnomalyStatus,
  AnomalySummary,
  AnomalyToolCallItem,
  AssignmentHistoryItem,
  CalculationDetail,
  ChiefDetail,
  ChiefForemanComparison,
  ChiefForemanItem,
  ChiefListItem,
  ContributionSummary,
  ContributionWorkCreatePayload,
  ContributionWorkItem,
  ContributionWorkUpdatePayload,
  CursorPage,
  DashboardSnapshot,
  DashboardSummary,
  FilterOptionsResponse,
  ForemanContributionSummary,
  ForemanDetail,
  ForemanKpiItem,
  ForemanListItem,
  KpiAnalysis,
  KpiListItem,
  KpiSummaryItem,
  MonthlyReportDetail,
  MonthlyReportLatest,
  MonthlyReportSummary,
  PlantDetail,
  PlantForemanItem,
  PlantListItem,
  PlantRankingItem,
  PlantShiftItem,
  PlantSummary,
  ReportExportMeta,
  ReportFormat,
  ReportType,
  ForemanShiftMatrixResponse,
  ShiftAnalysisCardsResponse,
  ShiftAnomalyDetail,
  ShiftComparisonItem,
  ShiftHeatmapResponse,
  TrendPoint,
} from "./types";

type Params = Record<string, string | number | undefined>;

function nextCursorParam(lastPage: CursorPage<unknown>): string | undefined {
  return lastPage.pagination.hasMore ? (lastPage.pagination.nextCursor ?? undefined) : undefined;
}

export function useAuthMe(enabled: boolean) {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => (await apiClient.get<AuthMeResponse>("/auth/me")).data,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useFilterOptions(plantIds?: string, factoryIds?: string) {
  return useQuery({
    queryKey: ["meta", "filters", plantIds, factoryIds],
    queryFn: async () => {
      const { data } = await apiClient.get<FilterOptionsResponse>("/meta/filters", {
        params: { plant_ids: plantIds, factory_ids: factoryIds },
      });
      return data;
    },
  });
}

export function useDashboardSummary(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "summary", params],
    queryFn: async () => (await apiClient.get<DashboardSummary>("/dashboard/summary", { params })).data,
  });
}

export function useDashboardSnapshot(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "snapshot", params],
    queryFn: async () => (await apiClient.get<DashboardSnapshot>("/dashboard/snapshot", { params })).data,
  });
}

export function useDashboardTrend(params: Params, granularity: string) {
  return useQuery({
    queryKey: ["dashboard", "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>("/dashboard/trend", { params: { ...params, granularity } })).data,
  });
}

export function useKpiSummary(params: Params, enabled = true) {
  return useQuery({
    enabled,
    queryKey: ["dashboard", "kpi-summary", params],
    queryFn: async () => (await apiClient.get<KpiSummaryItem[]>("/dashboard/kpi-summary", { params })).data,
  });
}

export function usePlantRanking(params: Params, order: "asc" | "desc", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "plant-ranking", params, order, limit],
    queryFn: async () =>
      (await apiClient.get<PlantRankingItem[]>("/dashboard/plant-ranking", { params: { ...params, order, limit } })).data,
  });
}

export function useShiftComparison(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "shift-comparison", params],
    queryFn: async () => (await apiClient.get<ShiftComparisonItem[]>("/dashboard/shift-comparison", { params })).data,
  });
}

export function useForemanRanking(params: Params, order: "asc" | "desc", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "foreman-ranking", params, order, limit],
    queryFn: async () =>
      (await apiClient.get<import("./types").ForemanRankingItem[]>("/dashboard/foreman-ranking", { params: { ...params, order, limit } })).data,
  });
}

export function useForemanTrendRanking(params: Params, direction: "improving" | "declining", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "foreman-trend-ranking", params, direction, limit],
    queryFn: async () =>
      (await apiClient.get<import("./types").ForemanTrendRankingItem[]>("/dashboard/foreman-trend-ranking", { params: { ...params, direction, limit } })).data,
  });
}

export function usePerformanceLeaders() {
  return useQuery({
    queryKey: ["dashboard", "performance-leaders"],
    queryFn: async () =>
      (await apiClient.get<import("./types").PerformanceLeadersResponse>("/dashboard/performance-leaders")).data,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePerformanceDistribution(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "distribution", params],
    queryFn: async () =>
      (await apiClient.get<import("./types").PerformanceDistributionResponse>("/dashboard/performance-distribution", { params })).data,
  });
}

export function usePlants(filters: Params, limit = 25) {
  return useInfiniteQuery({
    queryKey: ["plants", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (await apiClient.get<CursorPage<PlantListItem>>("/plants", { params: { ...filters, limit, cursor: pageParam } })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function usePlantDetail(plantId: string | undefined) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId],
    queryFn: async () => (await apiClient.get<PlantDetail>(`/plants/${plantId}`)).data,
  });
}

export function usePlantSummary(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "summary", params],
    queryFn: async () => (await apiClient.get<PlantSummary>(`/plants/${plantId}/summary`, { params })).data,
  });
}

export function usePlantKpis(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "kpis", params],
    queryFn: async () => (await apiClient.get<KpiSummaryItem[]>(`/plants/${plantId}/kpis`, { params })).data,
  });
}

export function usePlantShifts(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "shifts", params],
    queryFn: async () => (await apiClient.get<PlantShiftItem[]>(`/plants/${plantId}/shifts`, { params })).data,
  });
}

export function usePlantForemen(plantId: string | undefined, filters: Params, limit = 25) {
  return useInfiniteQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "foremen", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (
        await apiClient.get<CursorPage<PlantForemanItem>>(`/plants/${plantId}/foremen`, {
          params: { ...filters, limit, cursor: pageParam },
        })
      ).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function usePlantChiefs(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "chiefs", params],
    queryFn: async () => (await apiClient.get<import("./types").PlantChiefItem[]>(`/plants/${plantId}/chiefs`, { params })).data,
  });
}

export function useForemen(filters: Params, limit = 25) {
  return useInfiniteQuery({
    queryKey: ["foremen", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (await apiClient.get<CursorPage<ForemanListItem>>("/foremen", { params: { ...filters, limit, cursor: pageParam } })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function useForemenByIds(ids: string[]) {
  return useQuery({
    enabled: ids.length > 0,
    queryKey: ["foremen", "by-ids", ids],
    queryFn: async () =>
      (await apiClient.get<CursorPage<ForemanListItem>>("/foremen", { params: { ids: ids.join(","), limit: Math.max(ids.length, 1) } })).data,
  });
}

export function useForemanDetail(foremanId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, params],
    queryFn: async () => (await apiClient.get<ForemanDetail>(`/foremen/${foremanId}`, { params })).data,
  });
}

export function useForemanKpis(foremanId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "kpis", params],
    queryFn: async () => (await apiClient.get<ForemanKpiItem[]>(`/foremen/${foremanId}/kpis`, { params })).data,
  });
}

export function useForemanCalculationDetail(foremanId: string | undefined, kpiId: string | undefined) {
  return useQuery({
    enabled: !!foremanId && !!kpiId,
    queryKey: ["foremen", foremanId, "kpis", kpiId, "calculation-detail"],
    queryFn: async () => (await apiClient.get<CalculationDetail>(`/foremen/${foremanId}/kpis/${kpiId}/calculation-detail`)).data,
  });
}

export function useForemanTrend(foremanId: string | undefined, params: Params, granularity: string) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>(`/foremen/${foremanId}/trend`, { params: { ...params, granularity } })).data,
  });
}

export function useForemanAssignmentHistory(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "assignment-history"],
    queryFn: async () => (await apiClient.get<AssignmentHistoryItem[]>(`/foremen/${foremanId}/assignment-history`)).data,
  });
}

export function useForemanContributionSummary(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "contribution-summary"],
    queryFn: async () =>
      (await apiClient.get<ForemanContributionSummary>(`/foremen/${foremanId}/contribution-summary`)).data,
  });
}

export function useForemanMonthlyReports(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "monthly-reports"],
    queryFn: async () =>
      (await apiClient.get<MonthlyReportSummary[]>(`/foremen/${foremanId}/monthly-reports`)).data,
  });
}

export function useForemanMonthlyReportLatest(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "monthly-reports", "latest"],
    queryFn: async () =>
      (await apiClient.get<MonthlyReportLatest>(`/foremen/${foremanId}/monthly-reports/latest`)).data,
  });
}

export function useForemanMonthlyReport(foremanId: string | undefined, year: number | undefined, month: number | undefined) {
  return useQuery({
    enabled: !!foremanId && !!year && !!month,
    queryKey: ["foremen", foremanId, "monthly-reports", year, month],
    queryFn: async () =>
      (await apiClient.get<MonthlyReportDetail>(`/foremen/${foremanId}/monthly-reports/${year}/${month}`)).data,
  });
}

export function useForemanRecentContributions(foremanId: string | undefined, enabled: boolean) {
  return useQuery({
    enabled: !!foremanId && enabled,
    queryKey: ["foremen", foremanId, "contributions", "recent"],
    queryFn: async () =>
      (
        await apiClient.get<CursorPage<ContributionWorkItem>>("/contribution-works", {
          params: { foreman_ids: foremanId, status: "published", limit: 3 },
        })
      ).data,
  });
}

export function useChiefs(filters: Params, limit = 25) {
  return useInfiniteQuery({
    queryKey: ["chiefs", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (await apiClient.get<CursorPage<ChiefListItem>>("/chiefs", { params: { ...filters, limit, cursor: pageParam } })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function useChiefDetail(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, params],
    queryFn: async () => (await apiClient.get<ChiefDetail>(`/chiefs/${chiefId}`, { params })).data,
  });
}

export function useChiefForemen(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "foremen", params],
    queryFn: async () => (await apiClient.get<ChiefForemanItem[]>(`/chiefs/${chiefId}/foremen`, { params })).data,
  });
}

export function useChiefKpis(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "kpis", params],
    queryFn: async () => (await apiClient.get<ForemanKpiItem[]>(`/chiefs/${chiefId}/kpis`, { params })).data,
  });
}

export function useChiefForemanComparison(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "foreman-comparison", params],
    queryFn: async () => (await apiClient.get<ChiefForemanComparison>(`/chiefs/${chiefId}/foreman-comparison`, { params })).data,
  });
}

export function useChiefTrend(chiefId: string | undefined, params: Params, granularity: string) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>(`/chiefs/${chiefId}/trend`, { params: { ...params, granularity } })).data,
  });
}

export function useKpis() {
  return useQuery({
    queryKey: ["kpis"],
    queryFn: async () => (await apiClient.get<KpiListItem[]>("/kpis")).data,
  });
}

export function useKpiAnalysis(kpiId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!kpiId,
    queryKey: ["kpis", kpiId, "analysis", params],
    queryFn: async () => (await apiClient.get<KpiAnalysis>(`/kpis/${kpiId}/analysis`, { params })).data,
  });
}


export function useReportHistory(limit = 25) {
  return useInfiniteQuery({
    queryKey: ["reports", limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (await apiClient.get<CursorPage<ReportExportMeta>>("/reports", { params: { limit, cursor: pageParam } })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      reportType: ReportType; format: ReportFormat;
      dateFrom?: string; dateTo?: string;
      plantIds?: string[]; factoryIds?: string[]; chiefIds?: string[]; shiftIds?: string[]; kpiIds?: string[];
    }) => (await apiClient.post<ReportExportMeta>("/reports/generate", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function downloadReportUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/download`;
}

export function useContributionWorks(filters: Params, limit = 25) {
  return useInfiniteQuery({
    queryKey: ["contribution-works", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (
        await apiClient.get<CursorPage<ContributionWorkItem>>("/contribution-works", {
          params: { ...filters, limit, cursor: pageParam },
        })
      ).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function useContributionWork(id: string | undefined) {
  return useQuery({
    queryKey: ["contribution-works", id],
    queryFn: async () => (await apiClient.get<ContributionWorkItem>(`/contribution-works/${id}`)).data,
    enabled: !!id,
  });
}

export function useCreateContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ContributionWorkCreatePayload) =>
      (await apiClient.post<ContributionWorkItem>("/contribution-works", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useUpdateContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: ContributionWorkUpdatePayload }) =>
      (await apiClient.patch<ContributionWorkItem>(`/contribution-works/${id}`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useDeleteContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/contribution-works/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useContributionSummary(params: Params = {}) {
  return useQuery({
    queryKey: ["contribution-works", "summary", params],
    queryFn: async () => (await apiClient.get<ContributionSummary>("/contribution-works/summary", { params })).data,
  });
}


export function useAnomalies(filters: Params, limit = 25) {
  return useInfiniteQuery({
    queryKey: ["anomalies", filters, limit],
    queryFn: async ({ pageParam }: { pageParam?: string }) =>
      (await apiClient.get<CursorPage<AnomalyListItem>>("/anomalies", { params: { ...filters, limit, cursor: pageParam } })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursorParam,
  });
}

export function useAnomalySummary() {
  return useQuery({
    queryKey: ["anomalies", "summary"],
    queryFn: async () => (await apiClient.get<AnomalySummary>("/anomalies/summary")).data,
  });
}

export function useAnomaly(id: string | undefined) {
  return useQuery({
    queryKey: ["anomalies", id],
    queryFn: async () => (await apiClient.get<AnomalyDetail>(`/anomalies/${id}`)).data,
    enabled: !!id,
  });
}

export interface AnalyzeAnomalyPayload {
  id: string;
  mode?: AnalysisMode;
  forceRefresh?: boolean;
}

export function useAnalyzeAnomaly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: AnalyzeAnomalyPayload) =>
      (await apiClient.post<AnomalyDetail>(`/anomalies/${id}/analyze`, body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useReanalyzeAnomaly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: AnalyzeAnomalyPayload) =>
      (await apiClient.post<AnomalyDetail>(`/anomalies/${id}/reanalyze`, body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useUpdateAnomalyStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: AnomalyStatus }) =>
      (await apiClient.patch<AnomalyDetail>(`/anomalies/${id}/status`, { status })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useAnomalyInvestigation(id: string | undefined) {
  return useQuery({
    queryKey: ["anomalies", id, "investigation"],
    queryFn: async () => (await apiClient.get<AnomalyInvestigation>(`/anomalies/${id}/investigation`)).data,
    enabled: !!id,
  });
}

export function useAnalysisToolCalls(analysisId: string | undefined) {
  return useQuery({
    queryKey: ["analyses", analysisId, "tool-calls"],
    queryFn: async () =>
      (await apiClient.get<AnomalyToolCallItem[]>(`/analyses/${analysisId}/tool-calls`)).data,
    enabled: !!analysisId,
  });
}


export function useShiftAnalysisCards(params: Params) {
  return useQuery({
    queryKey: ["shift-analysis", "cards", params],
    queryFn: async () => (await apiClient.get<ShiftAnalysisCardsResponse>("/shift-analysis/cards", { params })).data,
  });
}

export function useShiftAnalysisDetail(params: { plant_id?: string; shift_id?: string; kpi_id?: string; month?: string }) {
  return useQuery({
    queryKey: ["shift-analysis", "detail", params],
    queryFn: async () => (await apiClient.get<ShiftAnomalyDetail>("/shift-analysis/detail", { params })).data,
    enabled: !!(params.plant_id && params.shift_id && params.kpi_id),
    placeholderData: keepPreviousData,
  });
}

export function useShiftHeatmap(params: Params) {
  return useQuery({
    queryKey: ["shift-analysis", "heatmap", params],
    queryFn: async () => (await apiClient.get<ShiftHeatmapResponse>("/shift-analysis/heatmap", { params })).data,
  });
}

export function usePlantForemanShiftMatrix(plantId: string | undefined, kpiId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId && !!kpiId,
    queryKey: ["plants", plantId, "foreman-shift-matrix", kpiId, params],
    queryFn: async () =>
      (
        await apiClient.get<ForemanShiftMatrixResponse>(`/plants/${plantId}/foreman-shift-matrix`, {
          params: { ...params, kpi_id: kpiId },
        })
      ).data,
  });
}
