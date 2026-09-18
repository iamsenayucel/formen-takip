from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Row, Select, and_, case, delete, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core import clock
from app.core.pagination import keyset_after
from app.models.contribution import ContributionGain, ContributionWork, ContributionWorkForeman, ContributionWorkPlant
from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    FinancialGainStatus,
    HighlightedGainMode,
    ImpactLevel,
)
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.schemas.common import parse_uuid_list
from app.services import contribution_calc as calc

TURKISH_COLLATION = "tr-TR-x-icu"


@dataclass
class ContributionWorkFilters:
    date_from: date | None = None
    date_to: date | None = None
    plant_ids: str | None = None
    factory_ids: str | None = None
    foreman_ids: str | None = None
    work_type: ContributionWorkType | None = None
    status: ContributionStatus | None = None
    impact_level: ImpactLevel | None = None
    financial_gain_status: FinancialGainStatus | None = None
    search: str | None = None
    # Authorization scope'undan gelen daraltma — kullanıcının `plant_ids` query param'ından
    # bağımsız, her zaman uygulanır. `None` = ALL (kısıtsız). Boş liste ise dahi bilerek
    # burada tutulur (`is not None` ile kontrol edilir) — string tabanlı `plant_ids` alanının
    # aksine, boş bir authorization scope "filtre yok" ile karıştırılmaz.
    scope_plant_ids: list[UUID] | None = None


@dataclass
class ContributionSummaryAggregates:
    total: int
    this_month: int
    total_gain_amount: float
    total_monthly_time_saving: float
    applicable_other_plants_count: int
    standardized_count: int
    by_plant: list[Row]
    by_type: list[Row]
    top_foremen: list[Row]


class ContributionWorkRepository:
    """ContributionWork / ContributionGain persistence erişimi.

    Yalnızca sorgu, ekleme, silme ve senkronizasyon işlemlerini kapsar.
    Business karar vermez (publish validation, status transition, override vb.)
    ve transaction'ı sonuçlandırmaz — `commit()` çağırmaz, yalnızca `flush()` yapabilir.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, work_id: UUID) -> ContributionWork | None:
        return self.db.get(ContributionWork, work_id)

    def get_gains(self, work_id: UUID) -> list[ContributionGain]:
        return list(self.db.scalars(select(ContributionGain).where(ContributionGain.work_id == work_id)))

    def foreman_refs(self, work_id: UUID) -> list[tuple[Foreman, ContributionRole]]:
        rows = self.db.execute(
            select(Foreman, ContributionWorkForeman.role)
            .join(ContributionWorkForeman, ContributionWorkForeman.foreman_id == Foreman.id)
            .where(ContributionWorkForeman.work_id == work_id)
            .order_by(Foreman.first_name)
        ).all()
        return [(f, role) for f, role in rows]

    def plant_refs(self, work_id: UUID) -> list[Plant]:
        return list(
            self.db.scalars(
                select(Plant)
                .options(joinedload(Plant.factory))
                .join(ContributionWorkPlant, ContributionWorkPlant.plant_id == Plant.id)
                .where(ContributionWorkPlant.work_id == work_id)
                .order_by(Plant.sequence_number)
            )
        )

    def foreman_ids(self, work_id: UUID) -> list[UUID]:
        return [
            row.foreman_id
            for row in self.db.scalars(
                select(ContributionWorkForeman).where(ContributionWorkForeman.work_id == work_id)
            )
        ]

    def plant_ids(self, work_id: UUID) -> list[UUID]:
        return [
            row.plant_id
            for row in self.db.scalars(select(ContributionWorkPlant).where(ContributionWorkPlant.work_id == work_id))
        ]

    def batch_gains(self, work_ids: list[UUID]) -> dict[UUID, list[ContributionGain]]:
        if not work_ids:
            return {}
        result: dict[UUID, list[ContributionGain]] = {}
        for g in self.db.scalars(select(ContributionGain).where(ContributionGain.work_id.in_(work_ids))):
            result.setdefault(g.work_id, []).append(g)
        return result

    def batch_foreman_refs(self, work_ids: list[UUID]) -> dict[UUID, list[tuple[Foreman, ContributionRole]]]:
        if not work_ids:
            return {}
        rows = self.db.execute(
            select(ContributionWorkForeman.work_id, Foreman, ContributionWorkForeman.role)
            .join(Foreman, Foreman.id == ContributionWorkForeman.foreman_id)
            .where(ContributionWorkForeman.work_id.in_(work_ids))
            .order_by(Foreman.first_name)
        ).all()
        result: dict[UUID, list[tuple[Foreman, ContributionRole]]] = {}
        for work_id, f, role in rows:
            result.setdefault(work_id, []).append((f, role))
        return result

    def batch_plant_refs(self, work_ids: list[UUID]) -> dict[UUID, list[Plant]]:
        if not work_ids:
            return {}
        rows = self.db.execute(
            select(ContributionWorkPlant.work_id, Plant)
            .options(joinedload(Plant.factory))
            .join(Plant, Plant.id == ContributionWorkPlant.plant_id)
            .where(ContributionWorkPlant.work_id.in_(work_ids))
            .order_by(Plant.sequence_number)
        ).all()
        result: dict[UUID, list[Plant]] = {}
        for work_id, p in rows:
            result.setdefault(work_id, []).append(p)
        return result

    def published_works_for_foreman(self, foreman_id: UUID) -> list[tuple[ContributionWork, ContributionRole]]:
        return list(
            self.db.execute(
                select(ContributionWork, ContributionWorkForeman.role)
                .join(ContributionWorkForeman, ContributionWorkForeman.work_id == ContributionWork.id)
                .where(
                    ContributionWorkForeman.foreman_id == foreman_id,
                    ContributionWork.status == ContributionStatus.PUBLISHED,
                )
            ).all()
        )

    def participant_counts(self, work_ids: list[UUID]) -> dict[UUID, int]:
        if not work_ids:
            return {}
        return dict(
            self.db.execute(
                select(ContributionWorkForeman.work_id, func.count())
                .where(ContributionWorkForeman.work_id.in_(work_ids))
                .group_by(ContributionWorkForeman.work_id)
            ).all()
        )

    # ------------------------------------------------------------------
    # Mutation işlemleri; commit çağıran katmana/service'e aittir
    # ------------------------------------------------------------------

    def add(self, work: ContributionWork) -> None:
        self.db.add(work)

    def delete(self, work: ContributionWork) -> None:
        self.db.delete(work)

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, work: ContributionWork) -> None:
        self.db.refresh(work)

    def sync_foremen(self, work_id: UUID, foreman_ids: list[UUID] | None) -> None:
        if foreman_ids is None:
            return
        self.db.execute(delete(ContributionWorkForeman).where(ContributionWorkForeman.work_id == work_id))
        unique_ids = list(dict.fromkeys(foreman_ids))
        solo_role = ContributionRole.LEAD if len(unique_ids) == 1 else ContributionRole.CONTRIBUTOR
        for fid in unique_ids:
            self.db.add(ContributionWorkForeman(work_id=work_id, foreman_id=fid, role=solo_role))

    def plant_ids_for_work(self, work_id: UUID) -> list[UUID]:
        return list(
            self.db.scalars(
                select(ContributionWorkPlant.plant_id).where(ContributionWorkPlant.work_id == work_id)
            )
        )

    def sync_plants(self, work_id: UUID, plant_ids: list[UUID] | None) -> None:
        if plant_ids is None:
            return
        self.db.execute(delete(ContributionWorkPlant).where(ContributionWorkPlant.work_id == work_id))
        for pid in dict.fromkeys(plant_ids):
            self.db.add(ContributionWorkPlant(work_id=work_id, plant_id=pid))

    def sync_gains(self, work_id: UUID, gains_input: list | None) -> None:
        if gains_input is None:
            return
        self.db.execute(delete(ContributionGain).where(ContributionGain.work_id == work_id))
        for g in gains_input:
            amount, percent = calc.compute_change(g.previous_value, g.next_value)
            self.db.add(
                ContributionGain(
                    work_id=work_id, gain_type=g.gain_type, gain_type_other_note=g.gain_type_other_note,
                    previous_value=g.previous_value, next_value=g.next_value,
                    change_amount=amount, change_percent=percent,
                    unit=g.unit, measurement_period=g.measurement_period, description=g.description,
                )
            )

    # ------------------------------------------------------------------
    # Filtering / sorting / listing
    # ------------------------------------------------------------------

    def build_filtered_query(self, filters: ContributionWorkFilters) -> Select:
        query = select(ContributionWork)

        plant_id_list = parse_uuid_list(filters.plant_ids)
        factory_id_list = parse_uuid_list(filters.factory_ids)
        foreman_id_list = parse_uuid_list(filters.foreman_ids)

        if filters.date_from:
            query = query.where(or_(ContributionWork.work_date >= filters.date_from, ContributionWork.work_date.is_(None)))
        if filters.date_to:
            query = query.where(or_(ContributionWork.work_date <= filters.date_to, ContributionWork.work_date.is_(None)))
        if plant_id_list:
            query = query.where(
                ContributionWork.id.in_(
                    select(ContributionWorkPlant.work_id).where(ContributionWorkPlant.plant_id.in_(plant_id_list))
                )
            )
        if filters.scope_plant_ids is not None:
            query = query.where(
                ContributionWork.id.in_(
                    select(ContributionWorkPlant.work_id).where(
                        ContributionWorkPlant.plant_id.in_(filters.scope_plant_ids)
                    )
                )
            )
        if factory_id_list:
            query = query.where(
                ContributionWork.id.in_(
                    select(ContributionWorkPlant.work_id)
                    .join(Plant, Plant.id == ContributionWorkPlant.plant_id)
                    .where(Plant.factory_id.in_(factory_id_list))
                )
            )
        if foreman_id_list:
            query = query.where(
                ContributionWork.id.in_(
                    select(ContributionWorkForeman.work_id).where(ContributionWorkForeman.foreman_id.in_(foreman_id_list))
                )
            )
        if filters.work_type:
            query = query.where(ContributionWork.work_type == filters.work_type)
        if filters.status:
            query = query.where(ContributionWork.status == filters.status)
        if filters.impact_level:
            query = query.where(ContributionWork.impact_level == filters.impact_level)
        if filters.financial_gain_status:
            query = query.where(ContributionWork.financial_gain_status == filters.financial_gain_status)
        if filters.search:
            like = f"%{filters.search}%"
            foreman_match = select(ContributionWorkForeman.work_id).join(
                Foreman, Foreman.id == ContributionWorkForeman.foreman_id
            ).where(func.concat(Foreman.first_name, " ", Foreman.last_name).ilike(like))
            query = query.where(
                or_(ContributionWork.title.ilike(like), ContributionWork.summary.ilike(like), ContributionWork.id.in_(foreman_match))
            )

        return query

    def _work_type_label_expr(self):
        return case(
            *[(ContributionWork.work_type == wt, label) for wt, label in WORK_TYPE_LABELS.items()],
            else_="",
        )

    def _foreman_name_sort_subquery(self):
        return (
            select(
                ContributionWorkForeman.work_id.label("work_id"),
                func.min(func.concat(Foreman.first_name, " ", Foreman.last_name).collate(TURKISH_COLLATION)).label(
                    "min_name"
                ),
            )
            .join(Foreman, Foreman.id == ContributionWorkForeman.foreman_id)
            .group_by(ContributionWorkForeman.work_id)
            .subquery()
        )

    def _plant_seq_sort_subquery(self):
        return (
            select(
                ContributionWorkPlant.work_id.label("work_id"),
                func.min(Plant.sequence_number).label("min_seq"),
            )
            .join(Plant, Plant.id == ContributionWorkPlant.plant_id)
            .group_by(ContributionWorkPlant.work_id)
            .subquery()
        )

    def _gain_bucket_sort_subquery(self):
        return (
            select(
                ContributionGain.work_id.label("work_id"),
                func.max(func.abs(ContributionGain.change_percent))
                .filter(ContributionGain.gain_type.in_(calc.CAPACITY_BUCKET))
                .label("best_capacity_pct"),
                func.max(func.abs(ContributionGain.change_percent))
                .filter(ContributionGain.gain_type.in_(calc.REDUCTION_BUCKET))
                .label("best_reduction_pct"),
                func.max(func.abs(ContributionGain.change_percent))
                .filter(ContributionGain.gain_type.in_(calc.QUALITY_SAFETY_ENERGY_BUCKET))
                .label("best_qse_pct"),
                func.max(func.abs(ContributionGain.change_percent)).label("best_any_pct"),
            )
            .where(ContributionGain.change_percent.is_not(None))
            .group_by(ContributionGain.work_id)
            .subquery()
        )

    def _gain_sort_expr(self, query):
        bucket_sq = self._gain_bucket_sort_subquery()
        referenced_gain = aliased(ContributionGain)

        query = query.outerjoin(bucket_sq, bucket_sq.c.work_id == ContributionWork.id).outerjoin(
            referenced_gain,
            and_(
                referenced_gain.work_id == ContributionWork.id,
                func.concat("gain:", referenced_gain.id) == ContributionWork.highlighted_gain_ref,
            ),
        )
        matched_gain_value = func.coalesce(referenced_gain.change_percent, referenced_gain.change_amount)

        is_manual = ContributionWork.highlighted_gain_mode == HighlightedGainMode.MANUAL
        sort_expr = case(
            (
                and_(is_manual, ContributionWork.highlighted_gain_ref == "financial", ContributionWork.gain_amount.is_not(None)),
                ContributionWork.gain_amount,
            ),
            (
                and_(
                    is_manual,
                    ContributionWork.highlighted_gain_ref == "time_saving",
                    ContributionWork.monthly_total_saving_minutes.is_not(None),
                ),
                ContributionWork.monthly_total_saving_minutes,
            ),
            (
                and_(is_manual, ContributionWork.highlighted_gain_ref.like("gain:%"), matched_gain_value.is_not(None)),
                matched_gain_value,
            ),
            (ContributionWork.gain_amount.is_not(None), ContributionWork.gain_amount),
            (ContributionWork.monthly_total_saving_minutes.is_not(None), ContributionWork.monthly_total_saving_minutes),
            (bucket_sq.c.best_capacity_pct.is_not(None), bucket_sq.c.best_capacity_pct),
            (bucket_sq.c.best_reduction_pct.is_not(None), bucket_sq.c.best_reduction_pct),
            (bucket_sq.c.best_qse_pct.is_not(None), bucket_sq.c.best_qse_pct),
            else_=bucket_sq.c.best_any_pct,
        )
        return query, sort_expr

    def count(self, query: Select) -> int:
        return self.db.scalar(select(func.count()).select_from(query.subquery())) or 0

    def list_page(
        self,
        filters: ContributionWorkFilters,
        *,
        sort_by: str,
        sort_dir: str,
        cursor_value: Any,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[ContributionWork]:
        query = self.build_filtered_query(filters)

        desc = sort_dir == "desc"
        if sort_by == "title":
            expr = ContributionWork.title.collate(TURKISH_COLLATION)
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "type":
            expr = self._work_type_label_expr().collate(TURKISH_COLLATION)
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "status":
            expr = ContributionWork.status
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "foreman":
            foreman_sq = self._foreman_name_sort_subquery()
            query = query.outerjoin(foreman_sq, foreman_sq.c.work_id == ContributionWork.id)
            expr = foreman_sq.c.min_name
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        elif sort_by == "plant":
            plant_sq = self._plant_seq_sort_subquery()
            query = query.outerjoin(plant_sq, plant_sq.c.work_id == ContributionWork.id)
            expr = plant_sq.c.min_seq
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        elif sort_by == "gain":
            query, expr = self._gain_sort_expr(query)
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        else:
            expr = ContributionWork.work_date
            order_terms = (
                [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
            )

        if cursor_id is not None:
            query = query.where(keyset_after(expr, sort_dir, cursor_value, ContributionWork.id, cursor_id))

        query = (
            query.add_columns(expr.label("sort_value"))
            .order_by(*order_terms, ContributionWork.id)
            .limit(limit + 1)
        )
        return [(row[0], row.sort_value) for row in self.db.execute(query)]

    # ------------------------------------------------------------------
    # Aggregates (summary)
    # ------------------------------------------------------------------

    def summary_aggregates(self, filters: ContributionWorkFilters) -> ContributionSummaryAggregates:
        query = self.build_filtered_query(filters)
        cw = query.subquery()
        work_ids_sq = select(cw.c.id)

        now_local = clock.now_local()
        month_start_local = now_local.date().replace(day=1)
        next_month_start_local = (
            date(now_local.year + 1, 1, 1) if now_local.month == 12
            else date(now_local.year, now_local.month + 1, 1)
        )
        month_start_utc = clock.local_datetime(month_start_local).astimezone(timezone.utc)
        next_month_start_utc = clock.local_datetime(next_month_start_local).astimezone(timezone.utc)

        totals = self.db.execute(
            select(
                func.count().label("total"),
                func.count()
                .filter(and_(cw.c.created_at >= month_start_utc, cw.c.created_at < next_month_start_utc))
                .label("this_month"),
                func.coalesce(func.sum(cw.c.gain_amount), 0).label("total_gain_amount"),
                func.coalesce(func.sum(cw.c.monthly_total_saving_minutes), 0).label("total_monthly_time_saving"),
                func.count().filter(cw.c.is_applicable_other_plants.is_(True)).label("applicable_other_plants_count"),
                func.count().filter(cw.c.is_standardized.is_(True)).label("standardized_count"),
            )
        ).one()

        by_plant_rows = self.db.execute(
            select(Plant.name, func.count())
            .select_from(ContributionWorkPlant)
            .join(Plant, Plant.id == ContributionWorkPlant.plant_id)
            .where(ContributionWorkPlant.work_id.in_(work_ids_sq))
            .group_by(Plant.name)
        ).all()

        by_type_rows = self.db.execute(
            select(cw.c.work_type, func.count()).where(cw.c.work_type.is_not(None)).group_by(cw.c.work_type)
        ).all()

        top_foremen_rows = self.db.execute(
            select(Foreman.id, Foreman.first_name, Foreman.last_name, func.count().label("cnt"))
            .select_from(ContributionWorkForeman)
            .join(Foreman, Foreman.id == ContributionWorkForeman.foreman_id)
            .where(ContributionWorkForeman.work_id.in_(work_ids_sq))
            .group_by(Foreman.id, Foreman.first_name, Foreman.last_name)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        return ContributionSummaryAggregates(
            total=totals.total,
            this_month=totals.this_month,
            total_gain_amount=totals.total_gain_amount,
            total_monthly_time_saving=totals.total_monthly_time_saving,
            applicable_other_plants_count=totals.applicable_other_plants_count,
            standardized_count=totals.standardized_count,
            by_plant=list(by_plant_rows),
            by_type=list(by_type_rows),
            top_foremen=list(top_foremen_rows),
        )


# Hem `_work_type_label_expr` (SQL sort) hem de ContributionWorkService'in sunum
# katmanı (work_type_label, by_work_type) tarafından kullanılan tek kaynak.
WORK_TYPE_LABELS = {
    ContributionWorkType.SMED: "SMED",
    ContributionWorkType.KAIZEN: "Kaizen",
    ContributionWorkType.PROBLEM_SOLVING: "Problem Çözme",
    ContributionWorkType.COST_REDUCTION: "Maliyet Azaltma",
    ContributionWorkType.TIME_SAVING: "Zaman Kazancı",
    ContributionWorkType.QUALITY_IMPROVEMENT: "Kalite İyileştirme",
    ContributionWorkType.SAFETY_IMPROVEMENT: "İş Güvenliği İyileştirmesi",
    ContributionWorkType.ENERGY_RESOURCE_SAVING: "Enerji veya Kaynak Tasarrufu",
    ContributionWorkType.PRODUCTION_EFFICIENCY: "Üretim Verimliliği",
    ContributionWorkType.DIGITALIZATION: "Dijitalleşme",
    ContributionWorkType.FIVE_S: "5S",
    ContributionWorkType.VARIETY_CHANGEOVER_EFFICIENCY: "Çeşit Dönüşü Verimliliği",
    ContributionWorkType.STAFF_SAVING: "Personel Tasarrufu",
    ContributionWorkType.CUSTOMER_COMPLAINT: "Müşteri Şikayet",
    ContributionWorkType.POKA_YOKE: "Poke Yoke",
    ContributionWorkType.OTHER: "Diğer",
}
