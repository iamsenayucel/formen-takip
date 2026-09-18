from __future__ import annotations

import calendar
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.common import Filters
from app.services.dashboard_foreman_service import DashboardForemanService
from app.services.monthly_foreman_report import latest_completed_period
from app.services.shift_analysis import month_label


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


class PerformanceLeadersService:
    def __init__(self, db: Session):
        self.db = db
        self.foreman_service = DashboardForemanService(db)

    def _month_leader(self, year: int, month: int, plant_ids: list[UUID] | None) -> dict | None:
        date_from, date_to = _month_bounds(year, month)
        filters = Filters(date_from=date_from, date_to=date_to, plant_ids=plant_ids)
        items = self.foreman_service.foreman_ranking(filters, order="desc", limit=1)["items"]
        if not items or not items[0]["is_reliable"]:
            return None
        return items[0]

    def leaders(self, plant_ids_scope: frozenset[UUID] | None = None) -> dict:
        year, month = latest_completed_period()
        _, month_end = _month_bounds(year, month)
        plant_ids = sorted(plant_ids_scope, key=str) if plant_ids_scope is not None else None

        monthly_leaders_by_month = {m: self._month_leader(year, m, plant_ids) for m in range(1, month + 1)}
        monthly_top = monthly_leaders_by_month[month]
        monthly_leader = (
            {
                "foreman_id": monthly_top["foreman_id"],
                "full_name": monthly_top["full_name"],
                "general_performance_score": monthly_top["general_performance_score"],
            }
            if monthly_top
            else None
        )

        ytd_filters = Filters(date_from=date(year, 1, 1), date_to=month_end, plant_ids=plant_ids)
        ytd_items = self.foreman_service.foreman_ranking(ytd_filters, order="desc", limit=1)["items"]
        yearly_leader = None
        if ytd_items and ytd_items[0]["is_reliable"]:
            top = ytd_items[0]
            monthly_wins = sum(
                1
                for leader in monthly_leaders_by_month.values()
                if leader and leader["foreman_id"] == top["foreman_id"]
            )
            yearly_leader = {
                "foreman_id": top["foreman_id"],
                "full_name": top["full_name"],
                "general_performance_score": top["general_performance_score"],
                "monthly_wins": monthly_wins,
            }

        return {
            "year": year,
            "last_calculated_month": {"year": year, "month": month, "label": month_label(month_end)},
            "monthly_leader": monthly_leader,
            "yearly_leader": yearly_leader,
        }
