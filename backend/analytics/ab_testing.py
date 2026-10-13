"""Sticky, weighted experiment assignment and prediction-linked feedback rewards."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.exc import IntegrityError

from core.database import (
    ABAssignment,
    ABExperiment,
    ABReward,
    ABVariantWeight,
    EventFeedback,
    Prediction,
    Profile,
    utcnow_naive,
)

DEFAULT_VARIANTS = ("control", "treatment")


def assign_variant(db: Any, user_id: int, task: str) -> str:
    existing = db.query(ABAssignment).filter_by(user_id=user_id, task=task).first()
    if existing is not None:
        return existing.variant
    variants = (
        db.query(ABVariantWeight)
        .filter_by(task=task)
        .order_by(ABVariantWeight.variant.asc())
        .all()
    )
    if not variants:
        variants = [
            ABVariantWeight(task=task, variant=name, weight=1.0)
            for name in DEFAULT_VARIANTS
        ]
        db.add_all(variants)
        db.flush()
    total = sum(row.weight for row in variants)
    threshold = secrets.randbelow(1_000_000) * total / 1_000_000
    cumulative = 0.0
    selected = variants[-1].variant
    for row in variants:
        cumulative += row.weight
        if threshold < cumulative:
            selected = row.variant
            break
    assignment = ABAssignment(user_id=user_id, task=task, variant=selected)
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.query(ABAssignment).filter_by(user_id=user_id, task=task).first()
        if winner is None:
            raise
        return winner.variant
    return selected


def record_experiment(
    db: Any,
    user_id: int,
    prediction_id: int | None,
    task: str,
    variant: str,
    latency_ms: int,
    success: bool,
) -> ABExperiment:
    result = ABExperiment(
        user_id=user_id,
        prediction_id=prediction_id,
        task=task,
        variant=variant,
        latency_ms=max(0, latency_ms),
        success=success,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def record_feedback_reward(
    db: Any,
    feedback: EventFeedback,
    profile: Profile,
) -> ABReward | None:
    if feedback.prediction_id is None:
        return None
    experiment = (
        db.query(ABExperiment)
        .join(Prediction, ABExperiment.prediction_id == Prediction.id)
        .filter(
            ABExperiment.prediction_id == feedback.prediction_id,
            Prediction.profile_id == profile.id,
        )
        .first()
    )
    if experiment is None:
        return None
    reward = max(0.0, 1.0 - abs(feedback.du_doan_score - feedback.thuc_te_score) / 100.0)
    row = ABReward(experiment_id=experiment.id, feedback_id=feedback.id, reward=reward)
    db.add(row)
    return row


def experiment_metrics(db: Any, user_id: int | None = None) -> dict[str, Any]:
    query = db.query(ABExperiment)
    if user_id is not None:
        query = query.filter(ABExperiment.user_id == user_id)
    experiments = query.all()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    experiment_ids = [row.id for row in experiments]
    rewards = (
        db.query(ABReward).filter(ABReward.experiment_id.in_(experiment_ids)).all()
        if experiment_ids
        else []
    )
    reward_by_experiment: dict[int, list[float]] = {}
    for row in rewards:
        reward_by_experiment.setdefault(row.experiment_id, []).append(row.reward)
    for experiment in experiments:
        key = (experiment.task, experiment.variant)
        item = grouped.setdefault(
            key,
            {
                "task": experiment.task,
                "variant": experiment.variant,
                "assignments": 0,
                "successful_predictions": 0,
                "latency_ms_total": 0,
                "feedback_count": 0,
                "reward_total": 0.0,
            },
        )
        item["assignments"] += 1
        item["successful_predictions"] += int(experiment.success)
        item["latency_ms_total"] += experiment.latency_ms
        values = reward_by_experiment.get(experiment.id, [])
        item["feedback_count"] += len(values)
        item["reward_total"] += sum(values)
    rows = []
    for item in grouped.values():
        count = item.pop("assignments")
        successes = item.pop("successful_predictions")
        latency_total = item.pop("latency_ms_total")
        reward_count = item.pop("feedback_count")
        reward_total = item.pop("reward_total")
        rows.append(
            {
                **item,
                "assignments": count,
                "success_rate": round(successes / count, 4) if count else None,
                "mean_latency_ms": round(latency_total / count) if count else None,
                "feedback_count": reward_count,
                "mean_reward": round(reward_total / reward_count, 4) if reward_count else None,
            }
        )
    return {
        "experiments": sorted(rows, key=lambda row: (row["task"], row["variant"])),
        "note": "Mô tả thử nghiệm nội bộ, không chứng minh hiệu quả khoa học.",
    }


def update_weights(db: Any, task: str, weights: dict[str, float]) -> dict[str, float]:
    for row in db.query(ABVariantWeight).filter_by(task=task).all():
        if row.variant not in weights:
            db.delete(row)
    for variant, weight in weights.items():
        row = db.query(ABVariantWeight).filter_by(task=task, variant=variant).first()
        if row is None:
            row = ABVariantWeight(task=task, variant=variant, weight=weight)
            db.add(row)
        else:
            row.weight = weight
            row.updated_at = utcnow_naive()
    db.commit()
    return weights
