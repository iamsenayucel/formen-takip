import enum


class CalculationType(str, enum.Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    RANGE_TARGET = "range_target"
    DIRECT_SCORE = "direct_score"
    PROPORTIONAL_PENALTY = "proportional_penalty"
    CUSTOM_FORMULA = "custom_formula"


class AggregationMethod(str, enum.Enum):
    SUM = "sum"
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    MIN = "min"
    MAX = "max"
    LAST_VALUE = "last_value"
    RATIO_RECOMPUTE = "ratio_recompute"


class TargetScopeType(str, enum.Enum):
    COMPANY = "company"
    PLANT = "plant"
    CHIEF = "chief"
    FOREMAN = "foreman"


class DataQualityStatus(str, enum.Enum):
    COMPLETE = "complete"
    MISSING = "missing"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    DUPLICATE = "duplicate"
    NEEDS_SOURCE_CORRECTION = "needs_source_correction"
    PENDING_RESYNC = "pending_resync"
    REPROCESSED = "reprocessed"


class IntegrationStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class SourceSystem(str, enum.Enum):
    SYNTHETIC = "SYNTHETIC"
    SAP = "SAP"


class SuccessDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class ReportType(str, enum.Enum):
    COMPANY_SUMMARY = "company_summary"
    PLANT_COMPARISON = "plant_comparison"
    SHIFT_COMPARISON = "shift_comparison"
    FOREMAN_PERFORMANCE = "foreman_performance"
    KPI_ANALYSIS = "kpi_analysis"
    CRITICAL_PERFORMANCE = "critical_performance"
    MISSING_DATA = "missing_data"


class ReportFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ReportStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class ReportStorageProvider(str, enum.Enum):
    S3 = "s3"
    LOCAL = "local"


class ReportGenerationStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ReportEmailStatus(str, enum.Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
    # Watchdog bu işin stale timeout sonrasında da SENDING kaldığını tespit etti.
    # SMTP idempotency garantisi vermediği için otomatik yeniden denenmez; "worker
    # göndermeden önce çöktü" ile "e-posta gönderildi, commit öncesi çöktü" ayrıştırılamaz.
    # `resolve-stale-email-job` ile açık operatör kararı gerekir.
    RECONCILIATION_REQUIRED = "reconciliation_required"


class ContributionWorkType(str, enum.Enum):
    SMED = "smed"
    KAIZEN = "kaizen"
    PROBLEM_SOLVING = "problem_solving"
    COST_REDUCTION = "cost_reduction"
    TIME_SAVING = "time_saving"
    QUALITY_IMPROVEMENT = "quality_improvement"
    SAFETY_IMPROVEMENT = "safety_improvement"
    ENERGY_RESOURCE_SAVING = "energy_resource_saving"
    PRODUCTION_EFFICIENCY = "production_efficiency"
    DIGITALIZATION = "digitalization"
    FIVE_S = "5s"
    VARIETY_CHANGEOVER_EFFICIENCY = "variety_changeover_efficiency"
    STAFF_SAVING = "staff_saving"
    CUSTOMER_COMPLAINT = "customer_complaint"
    POKA_YOKE = "poka_yoke"
    OTHER = "other"


class ContributionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class FinancialGainStatus(str, enum.Enum):
    YES = "yes"
    NO = "no"
    NOT_CALCULATED = "not_calculated"


class Currency(str, enum.Enum):
    TRY = "TRY"
    USD = "USD"
    EUR = "EUR"


class GainPeriod(str, enum.Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TimeUnit(str, enum.Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"


class RepeatPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ImpactLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OtherGainType(str, enum.Enum):
    CAPACITY_INCREASE = "capacity_increase"
    DOWNTIME_REDUCTION = "downtime_reduction"
    GSF_REDUCTION = "gsf_reduction"
    SCRAP_REDUCTION = "scrap_reduction"
    SLOW_RUNNING_REDUCTION = "slow_running_reduction"
    SAFETY_RISK_REDUCTION = "safety_risk_reduction"
    ENERGY_REDUCTION = "energy_reduction"
    LABOR_SAVING = "labor_saving"
    QUALITY_DEFECT_REDUCTION = "quality_defect_reduction"
    OTHER = "other"


class HighlightedGainMode(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ContributionRole(str, enum.Enum):
    LEAD = "lead"
    CONTRIBUTOR = "contributor"


class AnomalyType(str, enum.Enum):
    SHIFT_UNDERPERFORMANCE = "shift_underperformance"
    RISING_TREND = "rising_trend"
    FOREMAN_DEVIATION = "foreman_deviation"
    PRODUCT_GROUP_DEVIATION = "product_group_deviation"
    DOWNTIME_CONCENTRATION = "downtime_concentration"
    PLAN_ADHERENCE_STREAK = "plan_adherence_streak"
    PLANT_HISTORICAL_DEVIATION = "plant_historical_deviation"
    CROSS_PLANT_GAP = "cross_plant_gap"
    MULTI_KPI_SIMULTANEOUS = "multi_kpi_simultaneous"
    SINGLE_DAY_SPIKE = "single_day_spike"
    CHRONIC_ANOMALY = "chronic_anomaly"
    CRITICAL_PRODUCTION_LOSS = "critical_production_loss"
    DATA_QUALITY_SUSPECT = "data_quality_suspect"


class AnomalySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(str, enum.Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ACTION_PENDING = "action_pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AnomalyAnalysisStatus(str, enum.Enum):
    NOT_ANALYZED = "not_analyzed"
    ANALYZING = "analyzing"
    QUEUED = "queued"
    PLANNING = "planning"
    COLLECTING_DATA = "collecting_data"
    GENERATING_ANALYSIS = "generating_analysis"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class AnalysisMode(str, enum.Enum):
    SINGLE_CONTEXT = "single_context"
    TOOL_CALLING = "tool_calling"
