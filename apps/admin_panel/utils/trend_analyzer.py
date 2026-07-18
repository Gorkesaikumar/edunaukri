from datetime import timedelta
from decimal import Decimal
from typing import Union

from django.db.models import Sum, Count, QuerySet
from django.utils import timezone


class TrendAnalyzer:
    @staticmethod
    def calculate_growth(
        current_val: Union[int, Decimal, float],
        previous_val: Union[int, Decimal, float],
    ) -> dict:
        """Calculate period-over-period growth percentage and trend."""
        if previous_val == 0:
            if current_val == 0:
                pct = 0.0
            else:
                pct = 100.0
        else:
            pct = round(
                ((float(current_val) - float(previous_val)) / float(previous_val))
                * 100,
                1,
            )

        trend = "up" if pct > 0 else "down" if pct < 0 else "neutral"

        return {
            "current": current_val,
            "previous": previous_val,
            "growth_pct": pct,
            "trend": trend,
            "is_positive": pct > 0,
            "is_negative": pct < 0,
        }

    @staticmethod
    def get_period_filters(period_type: str = "month"):
        """Return date filters for current and previous periods."""
        now = timezone.now()

        if period_type == "day":
            start_current = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_current = now
            start_prev = start_current - timedelta(days=1)
            end_prev = start_current
        elif period_type == "week":
            start_current = now - timedelta(days=7)
            end_current = now
            start_prev = start_current - timedelta(days=7)
            end_prev = start_current
        else:  # month
            # Approximation for 30 days
            start_current = now - timedelta(days=30)
            end_current = now
            start_prev = start_current - timedelta(days=30)
            end_prev = start_current

        return (start_current, end_current), (start_prev, end_prev)

    @classmethod
    def analyze_queryset_count(
        cls, queryset: QuerySet, date_field: str = "created_at", period: str = "month"
    ) -> dict:
        (start_current, end_current), (start_prev, end_prev) = cls.get_period_filters(
            period
        )

        curr_count = queryset.filter(
            **{f"{date_field}__gte": start_current, f"{date_field}__lt": end_current}
        ).count()
        prev_count = queryset.filter(
            **{f"{date_field}__gte": start_prev, f"{date_field}__lt": end_prev}
        ).count()

        return cls.calculate_growth(curr_count, prev_count)

    @classmethod
    def analyze_queryset_sum(
        cls,
        queryset: QuerySet,
        sum_field: str,
        date_field: str = "created_at",
        period: str = "month",
    ) -> dict:
        (start_current, end_current), (start_prev, end_prev) = cls.get_period_filters(
            period
        )

        curr_val = (
            queryset.filter(
                **{
                    f"{date_field}__gte": start_current,
                    f"{date_field}__lt": end_current,
                }
            ).aggregate(total=Sum(sum_field))["total"]
            or 0
        )
        prev_val = (
            queryset.filter(
                **{f"{date_field}__gte": start_prev, f"{date_field}__lt": end_prev}
            ).aggregate(total=Sum(sum_field))["total"]
            or 0
        )

        return cls.calculate_growth(curr_val, prev_val)
