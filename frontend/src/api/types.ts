export interface PerformanceLevel {
  name: string;
  description: string;
  color: string;
  icon: string;
  outstandingPerformance?: boolean | null;
}

export interface FactoryOption {
  id: string;
  code: string;
  name: string;
  location: string;
}

export interface PlantOption {
  id: string;
  code: string;
  name: string;
  sequenceNumber: number;
  factoryId: string;
}

export interface ChiefOption {
  id: string;
  employeeNumber: string;
  name: string;
  plantIds: string[];
}

export interface FilterOption {
  id: string;
  code?: string | null;
  name: string;
  sequence?: number | null;
  unit?: string | null;
  weight?: number | null;
}

export interface FilterOptionsResponse {
  factories: FactoryOption[];
  plants: PlantOption[];
  chiefs: ChiefOption[];
  shifts: FilterOption[];
  kpis: FilterOption[];
}

export interface EntityRef {
  id: string;
  name: string | null;
  code?: string | null;
  score?: number;
}

export interface ApiError {
  code: string;
  message: string;
  requestId: string;
  timestamp: string;
  details?: { fields?: { field: string; reason: string; code?: string }[] } & Record<string, unknown> | null;
}

export interface CursorPagination {
  nextCursor: string | null;
  hasMore: boolean;
  total: number | null;
}

export interface CursorPage<T> {
  items: T[];
  pagination: CursorPagination;
}

export interface DashboardSummary {
  totalPlants: number;
  activePlants: number;
  totalActiveForemen: number;
  avgCompanyScore: number;
  foremenAboveTarget: number;
  foremenBelowTarget: number;
  foremenCritical: number;
  foremenSuccessful: number;
  foremenOutstanding: number;
  bestPlant: EntityRef | null;
  worstPlant: EntityRef | null;
  bestShift: EntityRef | null;
  worstShift: EntityRef | null;
  bestForeman: (EntityRef & { employeeNumber?: string }) | null;
  weakestKpi: { id: string; name: string; avgScore: number } | null;
  plantsWithMissingData: number;
  lastSyncAt: string | null;
  dataSource: string;
}

export interface TrendPoint {
  date: string;
  totalScore: number;
  isReliable: boolean;
}

export interface KpiSummaryItem {
  kpiId: string;
  code: string;
  name: string;
  unit: string;
  avgScore: number;
  avgTarget: number | null;
  avgActual: number | null;
  recordCount?: number;
}

export interface PlantRankingItem {
  plantId: string;
  code: string;
  name: string;
  totalScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface ShiftComparisonItem {
  shiftId: string;
  code: string | null;
  name: string | null;
  totalScore: number;
  recordCount: number;
  level: PerformanceLevel;
}

export interface PlantShiftItem {
  shiftId: string;
  code: string;
  name: string;
  totalScore: number;
  level: PerformanceLevel;
}

export interface ForemanRankingItem {
  foremanId: string;
  employeeNumber: string;
  fullName: string;
  operationalScore: number;
  contributionBonus: number;
  generalPerformanceScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface PlantForemanItem {
  foremanId: string;
  employeeNumber: string | null;
  fullName: string | null;
  operationalScore: number;
  contributionBonus: number;
  generalPerformanceScore: number;
  level: PerformanceLevel;
}

export interface ForemanTrendRankingItem {
  foremanId: string;
  employeeNumber: string;
  fullName: string;
  operationalScore: number;
  previousOperationalScore: number;
  delta: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface DistributionItem extends PerformanceLevel {
  count: number;
}

export interface PerformanceDistributionResponse {
  items: DistributionItem[];
  outstandingCount: number;
}

export interface PerformanceLeaderEntry {
  foremanId: string;
  fullName: string;
  generalPerformanceScore: number;
}

export interface PerformanceYearLeaderEntry extends PerformanceLeaderEntry {
  monthlyWins: number;
}

export interface PerformanceLeadersResponse {
  year: number;
  lastCalculatedMonth: { year: number; month: number; label: string };
  monthlyLeader: PerformanceLeaderEntry | null;
  yearlyLeader: PerformanceYearLeaderEntry | null;
}

export interface DashboardSnapshot {
  summary: DashboardSummary;
  kpiSummary: { items: KpiSummaryItem[] };
  shiftComparison: { items: ShiftComparisonItem[] };
  foremanRanking: {
    top: { items: ForemanRankingItem[] };
    bottom: { items: ForemanRankingItem[] };
  };
  foremanTrendRanking: {
    improving: { items: ForemanTrendRankingItem[] };
    declining: { items: ForemanTrendRankingItem[] };
  };
  performanceDistribution: PerformanceDistributionResponse;
}

export interface PlantGroupRef {
  id: string;
  code: string;
  score: number;
  supervisor: { id: string; name: string };
  foremen: { id: string; name: string }[];
}

export interface PlantListItem {
  id: string;
  code: string;
  name: string;
  sequenceNumber: number;
  factory: { id: string; code: string; name: string } | null;
  isActive: boolean;
  totalScore: number;
  level: PerformanceLevel;
  activeForemanCount: number;
  recordCount: number;
  group: PlantGroupRef | null;
}

export interface PlantDetail {
  id: string;
  code: string;
  name: string;
  sequenceNumber: number;
  factory: { id: string; code: string; name: string } | null;
  description: string | null;
  isActive: boolean;
  sapPlantCode: string | null;
}

export interface PlantSummary {
  plantId: string;
  totalScore: number;
  level: PerformanceLevel;
  foremenAverageScore: number;
  activeForemanCount: number;
  criticalForemanCount: number;
  strongestKpi: { id: string; name: string; avgScore: number } | null;
  weakestKpi: { id: string; name: string; avgScore: number } | null;
}

export interface PlantChiefItem {
  id: string;
  employeeNumber: string;
  fullName: string;
  foremanCount: number;
  totalScore: number;
  level: PerformanceLevel;
}

export interface ForemanAssignmentItem {
  plant: { id: string; name: string };
  chief: { id: string; name: string };
}

export interface ForemanListItem {
  id: string;
  employeeNumber: string;
  fullName: string;
  isActive: boolean;
  assignments: ForemanAssignmentItem[];
  operationalScore: number;
  contributionBonus: number;
  generalPerformanceScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface ContributionBonusBreakdownItem {
  workId: string;
  title: string;
  workType: string | null;
  score: number;
  workDate: string;
}

export interface ForemanDetail {
  id: string;
  employeeNumber: string;
  fullName: string;
  hireDate: string;
  isActive: boolean;
  phoneNumber: string | null;
  email: string | null;
  assignments: ForemanAssignmentItem[];
  operationalScore: number;
  contributionBonus: number;
  contributionBonusBreakdown: ContributionBonusBreakdownItem[];
  generalPerformanceScore: number;
  isReliable: boolean;
  inScope: boolean;
  level: PerformanceLevel;
  companyRank: number | null;
  companyTotal: number;
  plantRank: number | null;
  plantTotal: number;
}

export interface ChiefListItem {
  id: string;
  employeeNumber: string;
  code: string;
  fullName: string;
  isActive: boolean;
  plants: { id: string; name: string }[];
  factory: { id: string; code: string; name: string } | null;
  foremanCount: number;
  totalScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface ChiefDetail {
  id: string;
  employeeNumber: string;
  code: string;
  fullName: string;
  hireDate: string;
  isActive: boolean;
  phoneNumber: string | null;
  email: string | null;
  plants: { id: string; name: string }[];
  factory: { id: string; code: string; name: string } | null;
  foremanCount: number;
  totalScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
  companyRank: number | null;
  companyTotal: number;
  factoryRank: number | null;
  factoryTotal: number;
}

export interface ChiefForemanItem {
  id: string;
  employeeNumber: string | null;
  fullName: string | null;
  operationalScore: number;
  contributionBonus: number;
  generalPerformanceScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
}

export interface ForemanKpiItem {
  kpiId: string;
  code: string;
  name: string;
  description: string | null;
  unit: string;
  avgTarget: number | null;
  avgActual: number | null;
  avgRawScore: number;
  avgCappedScore: number;
  weight: number;
  weightedContributionSum: number;
  recordCount: number;
  evaluatedPlantCount: number;
  plants: {
    plantId: string;
    plantName: string | null;
    actual: number;
    target: number;
    score: number;
    weight: number;
    recordCount: number;
  }[];
  calculationVersion: number | null;
  calculationPeriod: { dateFrom: string; dateTo: string };
  dataQualityStatus: string;
  sourceSystem: string;
  agirGitme?: {
    signedValue: number;
    absoluteValue: number;
    direction: "OVERWEIGHT" | "UNDERWEIGHT" | "ON_TARGET";
    ratioToTarget: number | null;
  };
  inkita?: {
    includedTotal: number | null;
    includedComponents: string[];
    excludedComponents: string[];
    note: string;
  };
  planaUyum?: {
    avgAttainmentPct: number;
    plannedQty: number | null;
    actualQty: number | null;
    kgDiff: number | null;
    signedPctDeviation: number | null;
    direction: "ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN";
  };
}

export interface ForemanComparisonKpiMeta {
  kpiId: string;
  code: string;
  name: string;
  unit: string;
  decimalPlaces: number;
  weight: number;
}

export interface ForemanComparisonKpiValue {
  score: number;
  actual: number | null;
  target: number | null;
  recordCount: number;
}

export interface ForemanComparisonItem {
  id: string;
  employeeNumber: string | null;
  fullName: string | null;
  totalScore: number;
  isReliable: boolean;
  level: PerformanceLevel;
  kpiScores: Record<string, ForemanComparisonKpiValue | null>;
}

export interface ChiefForemanComparison {
  kpis: ForemanComparisonKpiMeta[];
  groupAverage: {
    totalScore: number;
    kpiScores: Record<string, number>;
  };
  foremen: ForemanComparisonItem[];
}

export interface CalculationDetail {
  performanceDate: string;
  targetValue: number | null;
  actualValue: number | null;
  unit: string;
  calculationType: string | null;
  calculationRuleParameters: Record<string, unknown> | null;
  calculationVersion: number;
  rawScore: number;
  cappedScore: number;
  minScore: number | null;
  maxScore: number | null;
  kpiWeight: number;
  weightedContribution: number;
  dataSource: string;
  sourceRecordId: string;
  planaUyum?: {
    plannedQty: number | null;
    actualQty: number | null;
    kgDiff: number | null;
    signedPctDeviation: number | null;
    status: "ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN";
    formulaVersion: number | null;
  };
}

export interface AssignmentHistoryItem {
  plant: string | null;
  chief: string | null;
  shift: string | null;
  startDate: string;
  endDate: string | null;
  isActive: boolean;
}

export interface MonthlyReportComparison {
  value: number;
  diff: number;
  diffPct: number | null;
  status: "above" | "at" | "below";
  isFavorable: boolean;
}

export interface MonthlyReportKpiEntry {
  kpiId: string;
  code: string;
  name: string;
  unit: string;
  weight: number;
  successDirectionHigher: boolean;
  hasData: boolean;
  recordCount: number;
  actual: number | null;
  score: number | null;
  level: PerformanceLevel | null;
  outstandingPerformance: boolean;
  vsPersonalTarget: MonthlyReportComparison | null;
  vsFactoryAverage: MonthlyReportComparison | null;
}

export interface MonthlyReportNote {
  kpiCode: string;
  name: string;
  text: string;
  managerPrompt?: string | null;
}

export interface MonthlyReportPreviousMonthKpi {
  code: string;
  name: string;
  diff: number;
  isImprovement: boolean;
}

export interface MonthlyReportData {
  foreman: { id: string; employeeNumber: string; fullName: string; hireDate: string };
  period: { year: number; month: number; label: string; dateFrom: string; dateTo: string };
  generatedAt: string;
  org: { factoryName: string | null; plants: { id: string; name: string }[]; chiefName: string | null } | null;
  organizationHistory?: {
    dateFrom: string;
    dateTo: string;
    factoryName: string | null;
    plants: { id: string; name: string }[];
    chiefName: string | null;
  }[];
  insufficientData: boolean;
  insufficientDataReason?: string;
  overall: {
    score: number;
    operationalScore: number;
    contributionBonus: number;
    level: PerformanceLevel;
    kpiCount: { total: number; aboveOrAtTarget: number; belowTarget: number; critical: number };
  } | null;
  summaryText?: string;
  closingText?: string;
  kpis?: MonthlyReportKpiEntry[];
  strengths?: MonthlyReportNote[];
  improvements?: MonthlyReportNote[];
  criticalAttention?: MonthlyReportNote[];
  congratulations?: { shown: boolean; text: string | null; kpiCodes: string[] };
  trend?: {
    weeklyPoints: { bucket: string; totalScore: number; isReliable: boolean }[];
    shape: "iyileşme" | "kötüleşme" | "stabil" | "dalgalı" | null;
    text: string | null;
  };
  previousMonth?: {
    available: boolean;
    label?: string;
    overallDiff?: number;
    perKpi?: MonthlyReportPreviousMonthKpi[];
  };
}

export interface MonthlyReportSummary {
  year: number;
  month: number;
  generatedAt: string;
  overallScore: number | null;
  overallLevelName: string | null;
  isReliable: boolean;
}

export interface MonthlyReportDetail extends MonthlyReportSummary {
  reportData: MonthlyReportData;
}

export interface MonthlyReportLatest extends Partial<MonthlyReportDetail> {
  available: boolean;
}

export interface MonthlyReportAccess {
  url: string;
  expiresAt: string | null;
  requiresAuth: boolean;
}

export interface KpiListItem {
  id: string;
  code: string;
  name: string;
  description: string;
  unit: string;
  calculationType: string;
  weight: number;
  defaultTargetValue: number;
  isCritical: boolean;
}

export interface KpiForemanValueItem {
  foremanId: string;
  fullName: string | null;
  avgActual: number;
  avgTarget: number;
  avgScore: number;
  recordCount: number;
  tier: "better" | "near" | "worse";
  level: PerformanceLevel | null;
}

export interface KpiAnalysis {
  kpi: { id: string; code: string; name: string; unit: string; decimalPlaces: number };
  companyAvgScore: number;
  companyAvgTarget: number | null;
  companyAvgActual: number | null;
  bestPlants: EntityRef[];
  worstPlants: EntityRef[];
  shiftComparison: { id: string; name: string; score: number }[];
  bestForemen: EntityRef[];
  worstForemen: EntityRef[];
  foremanValues: KpiForemanValueItem[];
  trend: { date: string; score: number }[];
}


export type ReportType =
  | "company_summary" | "plant_comparison" | "shift_comparison" | "foreman_performance"
  | "kpi_analysis" | "critical_performance" | "missing_data";
export type ReportFormat = "csv" | "xlsx" | "pdf";

export interface ReportExportMeta {
  id: string;
  fileName: string;
  reportType: string;
  format: string;
  rowCount: number;
  status?: string | null;
  requestedBy?: string | null;
  createdAt: string;
}

export type ContributionWorkType =
  | "smed" | "kaizen" | "problem_solving" | "cost_reduction" | "time_saving"
  | "quality_improvement" | "safety_improvement" | "energy_resource_saving"
  | "production_efficiency" | "digitalization"
  | "5s" | "variety_changeover_efficiency" | "staff_saving" | "customer_complaint" | "poka_yoke"
  | "other";
export type ContributionStatus = "draft" | "published";
export type FinancialGainStatus = "yes" | "no" | "not_calculated";
export type ContributionCurrency = "TRY" | "USD" | "EUR";
export type GainPeriod = "one_time" | "monthly" | "yearly";
export type ContributionTimeUnit = "second" | "minute" | "hour";
export type RepeatPeriod = "daily" | "weekly" | "monthly";
export type ImpactLevel = "low" | "medium" | "high";
export type OtherGainType =
  | "capacity_increase" | "downtime_reduction" | "gsf_reduction" | "scrap_reduction"
  | "slow_running_reduction" | "safety_risk_reduction" | "energy_reduction"
  | "labor_saving" | "quality_defect_reduction" | "other";
export type HighlightedGainMode = "auto" | "manual";

export type ContributionRole = "lead" | "contributor";

export interface ContributionForemanRef {
  id: string;
  name: string;
  employeeNumber: string;
  role: ContributionRole;
}

export interface ContributionPlantRef {
  id: string;
  name: string;
  code: string;
  factoryId: string;
  factoryName: string;
  factoryCode: string;
}

export interface ContributionGain {
  id: string;
  gainType: OtherGainType;
  gainTypeLabel: string;
  gainTypeOtherNote: string | null;
  previousValue: number | null;
  nextValue: number | null;
  changeAmount: number | null;
  changePercent: number | null;
  isImprovement: boolean | null;
  unit: string | null;
  measurementPeriod: string | null;
  description: string | null;
}

export interface ContributionGainInput {
  gainType: OtherGainType;
  gainTypeOtherNote?: string;
  previousValue?: number;
  nextValue?: number;
  unit?: string;
  measurementPeriod?: string;
  description?: string;
}

export interface ContributionHighlightedGain {
  source: string;
  label: string;
  value: number;
  unit: string | null;
}

export interface ContributionBeforeAfter {
  metricLabel: string;
  before: string;
  after: string;
  change: string;
  isImprovement: boolean;
}

export interface ContributionWorkItem {
  id: string;
  title: string;
  status: ContributionStatus;
  workType: ContributionWorkType | null;
  workTypeLabel: string | null;
  workTypeOtherNote: string | null;
  summary: string | null;
  detailedDescription: string | null;
  problemDescription: string | null;
  solutionDescription: string | null;
  resultDescription: string | null;
  foremen: ContributionForemanRef[];
  plants: ContributionPlantRef[];
  workDate: string | null;
  workDateEnd: string | null;
  impactLevel: ImpactLevel | null;
  createdBy: string | null;
  publishedAt: string | null;
  isStandardized: boolean;
  isApplicableOtherPlants: boolean;
  isPermanentSolution: boolean;
  workInstructionUpdated: boolean;
  financialGainStatus: FinancialGainStatus;
  gainAmount: number | null;
  currency: ContributionCurrency | null;
  gainPeriod: GainPeriod | null;
  calculationMethod: string | null;
  previousDuration: number | null;
  newDuration: number | null;
  durationUnit: ContributionTimeUnit | null;
  perOccurrenceSaving: number | null;
  repeatPeriod: RepeatPeriod | null;
  repeatCount: number | null;
  monthlyTotalSavingMinutes: number | null;
  gains: ContributionGain[];
  highlightedGainMode: HighlightedGainMode;
  highlightedGainRef: string | null;
  highlightedGain: ContributionHighlightedGain | null;
  beforeAfter: ContributionBeforeAfter | null;
  badges: string[];
  contributionScore: number | null;
  contributionScoreLabel: string | null;
  contributionScoreBreakdown: ContributionScoreCriterion[];
  createdAt: string;
  updatedAt: string;
}

export interface ContributionScoreCriterion {
  label: string;
  points: number;
  detail: string;
}

export interface ContributionWorkCreatePayload {
  title: string;
  status?: ContributionStatus;
  workType?: ContributionWorkType;
  workTypeOtherNote?: string;
  summary?: string;
  detailedDescription?: string;
  problemDescription?: string;
  solutionDescription?: string;
  resultDescription?: string;
  foremanIds?: string[];
  plantIds?: string[];
  workDate?: string;
  workDateEnd?: string;
  impactLevel?: ImpactLevel;
  isStandardized?: boolean;
  isApplicableOtherPlants?: boolean;
  isPermanentSolution?: boolean;
  workInstructionUpdated?: boolean;
  financialGainStatus?: FinancialGainStatus;
  gainAmount?: number;
  currency?: ContributionCurrency;
  gainPeriod?: GainPeriod;
  calculationMethod?: string;
  previousDuration?: number;
  newDuration?: number;
  durationUnit?: ContributionTimeUnit;
  repeatPeriod?: RepeatPeriod;
  repeatCount?: number;
  perOccurrenceSaving?: number;
  monthlyTotalSavingMinutes?: number;
  gains?: ContributionGainInput[];
  highlightedGainMode?: HighlightedGainMode;
  highlightedGainRef?: string;
}

export type ContributionWorkUpdatePayload = Partial<ContributionWorkCreatePayload>;

export interface ForemanContributionSummary {
  totalContributions: number;
  smedCount: number;
  ledContributions: number;
  financialGain: Record<string, number>;
  totalTimeSavingMinutes: number;
  lastContributionDate: string | null;
}

export interface ContributionSummary {
  totalWorks: number;
  addedThisMonth: number;
  totalGainAmount: number;
  totalMonthlyTimeSavingMinutes: number;
  byPlant: { name: string; count: number }[];
  byWorkType: { label: string; count: number }[];
  topForemen: { id: string; name: string; count: number }[];
  applicableOtherPlantsCount: number;
  standardizedRatio: number;
}


export type AnomalySeverity = "low" | "medium" | "high" | "critical";
export type AnomalyStatus = "new" | "in_review" | "action_pending" | "resolved" | "closed";
export type AnomalyAnalysisStatus =
  | "not_analyzed" | "analyzing" | "queued" | "planning" | "collecting_data" | "generating_analysis"
  | "completed" | "completed_with_warnings" | "failed" | "timed_out" | "cancelled";
export type AnalysisMode = "single_context" | "tool_calling";

export interface AnomalyListItem {
  id: string;
  code: string;
  title: string;
  factoryCode: string | null;
  factoryName: string | null;
  plantId: string;
  plantName: string | null;
  shiftId: string | null;
  shiftName: string | null;
  kpiId: string;
  kpiCode: string | null;
  kpiName: string | null;
  anomalyType: string;
  anomalyTypeLabel: string;
  detectedAt: string;
  periodStart: string;
  periodEnd: string;
  deviationPercent: number;
  mlConfidence: number;
  severity: AnomalySeverity;
  severityLabel: string;
  status: AnomalyStatus;
  statusLabel: string;
  analysisStatus: AnomalyAnalysisStatus;
  analysisStatusLabel: string;
}

export interface AnomalyEvidenceItem {
  type: string;
  label: string;
  value: number;
  unit: string;
}

export interface AnomalyRelatedSignal {
  kpi: string;
  kpiCode: string;
  value: number;
  changePercent: number;
  direction: "increase" | "decrease";
}

export interface AnomalyDailyPoint {
  date: string;
  value: number;
}

export type KpiDirection = "high" | "low" | null;

export interface AnomalyKpiDefinition {
  name: string | null;
  description: string | null;
  desiredDirection: KpiDirection;
  warningThreshold: number | null;
  criticalThreshold: number | null;
}

export type AnalysisConfidence = "low" | "medium" | "high";
export type AnalysisPriority = "low" | "medium" | "high" | "critical";
export type AnalysisRiskLevel = "low" | "medium" | "high" | "critical";

export interface AnalysisSourceRef {
  toolCallId: string;
  toolName: string;
}

export interface AnalysisVerifiedFinding {
  findingId?: string;
  finding: string;
  evidence: string;
  sourceRefs: AnalysisSourceRef[];
}

export interface AnalysisPossibleCause {
  cause: string;
  confidence: AnalysisConfidence;
  supportingEvidence: string[];
  contradictingEvidence: string[];
  sourceRefs: AnalysisSourceRef[];
  verificationRequired: string;
}

export interface AnalysisRecommendedInvestigation {
  step: string;
  responsibleUnit: string;
  priority: AnalysisPriority;
  expectedOutput: string;
}

export interface AnalysisImmediateAction {
  action: string;
  responsibleUnit: string;
  priority: AnalysisPriority;
  timeframe: string;
  expectedImpact: string;
  requiresApproval: boolean;
}

export interface AnalysisMediumTermAction {
  action: string;
  responsibleUnit: string;
  expectedImpact: string;
}

export interface AnalysisToolUsedRef {
  toolName: string;
  toolCallId: string;
  purpose: string;
}

export interface AnalysisDataScope {
  startDate: string;
  endDate: string;
  recordCount: number;
  dataQualityStatus: string;
}

export interface AnalysisResult {
  executiveSummary: string;
  verifiedFindings: AnalysisVerifiedFinding[];
  possibleCauses: AnalysisPossibleCause[];
  recommendedInvestigations: AnalysisRecommendedInvestigation[];
  immediateActions: AnalysisImmediateAction[];
  mediumTermActions: AnalysisMediumTermAction[];
  missingInformation: string[];
  riskLevel: AnalysisRiskLevel;
  analysisConfidence: number;
  requiresHumanReview: boolean;
  toolsUsed: AnalysisToolUsedRef[];
  dataScope: AnalysisDataScope | null;
  analysisLimitations: string[];
  disclaimer: string;
}

export interface AnomalyAnalysisRecord {
  id: string;
  code: string;
  mode: AnalysisMode;
  status: AnomalyAnalysisStatus;
  statusLabel: string;
  isDemo: boolean;
  model: string;
  result: AnalysisResult | null;
  investigationPlan: string[] | null;
  toolCallCount: number;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string;
  completedAt: string | null;
}

export interface AnomalyToolCallItem {
  id: string;
  code: string;
  stepNumber: number;
  toolName: string;
  toolLabel: string;
  arguments: Record<string, unknown>;
  status: "success" | "error" | "timeout";
  result: Record<string, unknown> | null;
  recordCount: number | null;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
}

export interface AnomalyDetail extends AnomalyListItem {
  description: string;
  observedValue: number;
  expectedValue: number;
  targetValue: number | null;
  unit: string;
  affectedDays: number | null;
  totalDays: number | null;
  comparison: Record<string, number>;
  relatedSignals: AnomalyRelatedSignal[];
  evidence: AnomalyEvidenceItem[];
  foremanCodes: string[];
  dataQualityStatus: string;
  dataQualityWarnings: string[];
  dailyHistory: AnomalyDailyPoint[];
  kpiDefinition: AnomalyKpiDefinition;
  latestAnalysis: AnomalyAnalysisRecord | null;
  analysisHistory: AnomalyAnalysisRecord[];
}

export interface AnomalySummary {
  totalActive: number;
  criticalCount: number;
  highCount: number;
  pendingAnalysisCount: number;
  openedLast7Days: number;
  resolvedCount: number;
}

export interface ForemanRef {
  id: string;
  name: string;
  employeeNumber: string;
}

export interface ForemanKpiTrendPoint {
  periodLabel: string;
  avgActual: number | null;
  hasData: boolean;
}

export interface ResponsibleForeman {
  resolved: boolean;
  shiftSpecific: boolean;
  reason: string | null;
  note: string | null;
  primary: (ForemanRef & { dayCount?: number | null; totalDays?: number | null }) | null;
  others: (ForemanRef & { dayCount?: number | null })[];
  kpiTrend: ForemanKpiTrendPoint[];
}

export interface BaselineComparison {
  available: boolean;
  reason?: string;
  baselinePeriod?: { start: string; end: string; days: number };
  currentPeriod?: { start: string; end: string; days: number };
  baselineAvg?: number;
  currentAvg?: number;
  absChange?: number;
  pctChange?: number | null;
  direction?: "improved" | "worsened" | "unchanged";
}

export interface RelatedKpiChange {
  kpi: string;
  kpiCode: string;
  baselineValue: number;
  currentValue: number;
  absChange: number;
  changePercent: number;
  direction: "increase" | "decrease";
  performanceDirection: "improved" | "worsened" | null;
  sparkline: number[];
}

export interface DowntimeCategory {
  category: string;
  totalMinutes: number;
  occurrenceCount: number;
}

export interface DowntimeBreakdown {
  plantName: string;
  shiftName: string;
  periodDays: number;
  totalDowntimeMinutes: number;
  totalDowntimeCount: number;
  categories: DowntimeCategory[];
  topReasons: string[];
  longestSingleEventMinutes: number;
  previousPeriodTotalMinutes: number;
  otherShiftsAverageMinutes: number | null;
}

export interface InvestigationImpact {
  additionalDowntimeMinutes: number | null;
  additionalDowntimeNote: string | null;
  productionLossNote: string;
  costNote: string;
}

export interface SimilarCase {
  anomalyId: string;
  anomalyCode: string;
  title: string;
  plantName: string | null;
  kpiName: string | null;
  anomalyTypeLabel: string;
  similarityReason: string;
  detectedAt: string;
  resolutionStatus: "resolved" | "open";
  verifiedRootCause: string | null;
  actionTaken: string | null;
  actionResult: string | null;
  kpiValueBefore: number;
  kpiValueAfter: number | null;
}

export interface ShiftComparisonEntry {
  shiftId: string;
  code: string;
  name: string;
  value: number | null;
  isAnomalyShift: boolean;
}

export interface FactoryComparisonEntry {
  code: string;
  name: string;
  value: number | null;
  isAnomalyFactory: boolean;
}

export interface PreviousMonthComparison {
  available: boolean;
  label?: string;
  period?: { start: string; end: string };
  value?: number | null;
  currentValue?: number;
  changePercent?: number | null;
}

export interface AnomalyInvestigation {
  responsibleForeman: ResponsibleForeman;
  baselineComparison: BaselineComparison;
  relatedKpiChanges: RelatedKpiChange[];
  downtimeBreakdown: DowntimeBreakdown | null;
  impact: InvestigationImpact;
  similarCases: SimilarCase[];
  shiftComparison: ShiftComparisonEntry[];
  factoryComparison: FactoryComparisonEntry[];
  previousMonth: PreviousMonthComparison;
  comparisonTargetValue: number | null;
}


export type ShiftAnomalySeverity = "medium" | "high";

export interface ShiftAnalysisPeriod {
  monthStart: string;
  monthEnd: string;
  label: string;
}

export interface ShiftAnalysisSummary {
  period: ShiftAnalysisPeriod;
  totalAnomalies: number;
  highCount: number;
  mediumCount: number;
  topPlant: { id: string; name: string; count: number } | null;
  topKpi: { id: string; name: string; count: number } | null;
  maxPctDiff: number | null;
}

export interface ShiftAnomalyForemanStat {
  id: string;
  name: string;
  employeeNumber: string;
  avgActual: number;
  recordCount: number;
  weekCount: number;
}

export interface ShiftAnomalyCard {
  id: string;
  plantId: string;
  plantName: string;
  plantSequence: number;
  factoryId: string;
  factoryCode: string;
  shiftId: string;
  shiftName: string;
  kpiId: string;
  kpiCode: string;
  kpiName: string;
  kpiUnit: string;
  kpiDecimalPlaces: number;
  successDirectionHigher: boolean;
  severity: ShiftAnomalySeverity;
  title: string;
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  absDiff: number;
  pctDiff: number;
  comparedWeeks: number;
  period: ShiftAnalysisPeriod;
}

export interface ShiftAnalysisCardsResponse {
  items: ShiftAnomalyCard[];
  summary: ShiftAnalysisSummary;
}

export interface ShiftWeeklyForemanPoint {
  assigned: boolean;
  value: number | null;
  dayCount: number;
  hasSufficientData: boolean;
  shiftId: string | null;
  shiftName: string | null;
}

export interface ShiftWeeklyComparisonPoint {
  weekIndex: number;
  weekLabel: string;
  better: ShiftWeeklyForemanPoint;
  worse: ShiftWeeklyForemanPoint;
}

export interface ShiftAnomalyCrossKpiSignal {
  kpiId: string;
  kpiCode: string;
  kpiName: string;
  pctDiff: number;
  severity: ShiftAnomalySeverity;
  sameForemanBetter: boolean;
}

export interface ShiftAnomalyDetail extends ShiftAnomalyCard {
  referenceTarget: number;
  weeklyComparison: ShiftWeeklyComparisonPoint[];
  crossKpiSignals: ShiftAnomalyCrossKpiSignal[];
  patternHeadline: string;
  patternDetail: string;
  isRecurringPattern: boolean;
}


export type HeatmapLevel = "no_data" | "normal" | "attention" | "significant" | "critical";

export interface HeatmapShiftPoint {
  avgActual: number;
  recordCount: number;
}

export interface HeatmapCell {
  plantId: string;
  kpiId: string;
  level: HeatmapLevel;
  v1: HeatmapShiftPoint | null;
  v2: HeatmapShiftPoint | null;
  absDiff: number | null;
  pctDiff: number | null;
  betterShiftId: string | null;
}

export interface HeatmapPlantRef {
  id: string;
  name: string;
  sequenceNumber: number;
  factoryCode: string;
}

export interface HeatmapKpiRef {
  id: string;
  code: string;
  name: string;
  unit: string;
}

export interface ShiftHeatmapSummary {
  anomalyPlantCount: number;
  criticalCellCount: number;
  priorityPlantCount: number;
  topKpi: { id: string; name: string; count: number } | null;
}

export interface ShiftHeatmapResponse {
  period: ShiftAnalysisPeriod;
  shifts: { id: string; code: string; name: string }[];
  plants: HeatmapPlantRef[];
  kpis: HeatmapKpiRef[];
  cells: HeatmapCell[];
  summary: ShiftHeatmapSummary;
}


export interface ForemanShiftMatrixCell {
  avgActual: number;
  avgTarget: number;
  score: number;
  recordCount: number;
  deviationPct: number | null;
  level: PerformanceLevel;
}

export interface ForemanShiftMatrixRow {
  foremanId: string;
  fullName: string;
  employeeNumber: string;
  cells: Record<string, ForemanShiftMatrixCell | null>;
}

export interface ForemanShiftMatrixResponse {
  kpi: { id: string; code: string; name: string; unit: string; successDirectionHigher: boolean };
  referenceTarget: number;
  shifts: { id: string; code: string; name: string }[];
  rows: ForemanShiftMatrixRow[];
  insight: string;
}
