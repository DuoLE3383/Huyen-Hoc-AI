"""Descriptive feedback metrics; none of these measures validate predictions scientifically."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from database import EventFeedback, utcnow_naive

EVENT_TYPES = {"tai_van", "tinh_duyen", "su_nghiep", "suc_khoe", "gap_go", "thay_doi"}


def _feedback_rows(
    db: Session,
    profile_ids: list[int],
    since: datetime | None = None,
) -> list[EventFeedback]:
    if not profile_ids:
        return []
    query = db.query(EventFeedback).filter(EventFeedback.profile_id.in_(profile_ids))
    if since is not None:
        query = query.filter(EventFeedback.created_at >= since)
    return query.order_by(EventFeedback.created_at.asc()).all()


def accuracy_by_field(db: Session, profile_ids: list[int], days: int = 90) -> dict[str, Any]:
    since = utcnow_naive() - timedelta(days=days)
    rows = _feedback_rows(db, profile_ids, since)
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row.loai_su_kien, []).append(
            abs(row.du_doan_score - row.thuc_te_score)
        )
    fields = []
    for event_type, errors in grouped.items():
        mae = sum(errors) / len(errors)
        fields.append({
            "linh_vuc": event_type,
            "so_mau": len(errors),
            "mae": round(mae, 1),
            "do_chinh_xac": round(max(0, 100 - mae), 1),
        })
    fields.sort(key=lambda item: item["do_chinh_xac"], reverse=True)
    return {"fields": fields, "tong_feedback": len(rows)}


def accuracy_timeline(
    db: Session, profile_ids: list[int], weeks: int = 12
) -> dict[str, list[dict[str, Any]]]:
    rows = _feedback_rows(db, profile_ids, utcnow_naive() - timedelta(weeks=weeks))
    buckets: dict[str, list[float]] = {}
    for row in rows:
        year, week, _ = row.created_at.isocalendar()
        key = f"{year}-W{week:02d}"
        buckets.setdefault(key, []).append(abs(row.du_doan_score - row.thuc_te_score))
    timeline = []
    for key, errors in sorted(buckets.items()):
        mae = sum(errors) / len(errors)
        timeline.append({
            "tuan": key,
            "so_mau": len(errors),
            "mae": round(mae, 1),
            "do_chinh_xac": round(max(0, 100 - mae), 1),
        })
    return {"timeline": timeline}


def bias_analysis(db: Session, profile_ids: list[int]) -> dict[str, Any]:
    rows = _feedback_rows(db, profile_ids)
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row.loai_su_kien, []).append(
            row.thuc_te_score - row.du_doan_score
        )
    if not grouped:
        return {"bias": [], "tong_ket": "Chưa có dữ liệu"}
    bias = []
    for event_type, differences in grouped.items():
        average = sum(differences) / len(differences)
        trend = (
            "điểm chỉ số cao hơn đánh giá thực tế"
            if average < -5
            else "điểm chỉ số thấp hơn đánh giá thực tế"
            if average > 5
            else "khá cân bằng"
        )
        bias.append({
            "linh_vuc": event_type,
            "bias_trung_binh": round(average, 1),
            "xu_huong": trend,
            "so_mau": len(differences),
        })
    return {"bias": sorted(bias, key=lambda item: item["linh_vuc"])}


def top_patterns(db: Session, profile_ids: list[int]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[float]] = {}
    for row in _feedback_rows(db, profile_ids):
        grouped.setdefault(row.scope or "general", []).append(
            abs(row.du_doan_score - row.thuc_te_score)
        )
    scopes = []
    for scope, errors in grouped.items():
        mae = sum(errors) / len(errors)
        scopes.append({
            "scope": scope,
            "so_mau": len(errors),
            "do_chinh_xac": round(max(0, 100 - mae), 1),
        })
    return {"scopes": sorted(scopes, key=lambda item: -item["do_chinh_xac"])}


def get_weights_from_history(
    db: Session,
    profile_ids: list[int],
    days: int = 90,
    min_samples: int = 5,
) -> dict[str, float]:
    """Return bounded experimental scaling hints, neutral when evidence is sparse."""
    weights = {event_type: 1.0 for event_type in EVENT_TYPES}
    rows = _feedback_rows(db, profile_ids, utcnow_naive() - timedelta(days=days))
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if row.loai_su_kien in EVENT_TYPES:
            grouped.setdefault(row.loai_su_kien, []).append(
                abs(row.du_doan_score - row.thuc_te_score)
            )
    for event_type, errors in grouped.items():
        if len(errors) < min_samples:
            continue
        mae = sum(errors) / len(errors)
        # The resulting multiplier is only a heuristic, not a learned model parameter.
        weights[event_type] = round(max(0.5, min(1.5, 1.5 - mae / 100)), 2)
    return weights


def apply_experimental_weights(
    scores: dict[str, float], weights: dict[str, float]
) -> dict[str, float]:
    return {
        key: round(max(0.0, min(100.0, value * weights.get(key, 1.0))), 2)
        for key, value in scores.items()
    }
