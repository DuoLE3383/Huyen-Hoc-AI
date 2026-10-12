"""Build an opt-in, manually approved SFT dataset from linked feedback."""

import argparse
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

if __package__:
    from .database import EventFeedback, Prediction, Profile, SessionLocal, User
else:
    from database import EventFeedback, Prediction, Profile, SessionLocal, User

SYSTEM_PROMPT = (
    "Bạn viết diễn giải huyền học Việt Nam để tham khảo/giải trí. "
    "Không khẳng định chắc chắn về tương lai, không đưa lời khuyên y tế, "
    "pháp lý hoặc tài chính mang tính quyết định. Chỉ trả JSON."
)


def _contains_personal_details(value: Any, private_values: tuple[str, ...]) -> bool:
    if isinstance(value, str):
        return any(
            re.search(
                rf"(?<!\w){re.escape(private_value)}(?!\w)",
                value,
                flags=re.IGNORECASE,
            )
            is not None
            for private_value in private_values
        )
    if isinstance(value, list):
        return any(_contains_personal_details(item, private_values) for item in value)
    if isinstance(value, dict):
        return any(_contains_personal_details(item, private_values) for item in value.values())
    return False


def _training_record(feedback: EventFeedback, prediction: Prediction, profile: Profile) -> dict:
    analysis = json.loads(prediction.du_doan_json)
    scores = json.loads(prediction.chi_so_json)
    profile_data = json.loads(profile.profile_json)
    if not isinstance(analysis, dict) or not isinstance(scores, dict):
        raise ValueError("Prediction data must contain JSON objects.")
    birth_date = datetime.strptime(profile.ngay_sinh, "%d/%m/%Y").date()
    private_values = (
        birth_date.strftime("%d/%m/%Y"),
        birth_date.isoformat(),
        birth_date.strftime("%d-%m-%Y"),
        birth_date.strftime("%Y/%m/%d"),
        birth_date.strftime("%d%m%Y"),
        f"{birth_date.day} tháng {birth_date.month} năm {birth_date.year}",
    )
    full_name = profile_data.get("ho_ten", "")
    if isinstance(full_name, str) and full_name.strip():
        private_values += (full_name.strip(),)
    if _contains_personal_details(analysis, private_values):
        raise ValueError("Generated response contains profile identifiers.")
    user_prompt = (
        "Hãy tạo bài phân tích theo các chỉ số tham khảo sau. "
        "Điểm feedback là đánh giá chủ quan, không phải bằng chứng khoa học.\n"
        f"Lĩnh vực feedback: {feedback.loai_su_kien}\n"
        f"Chỉ số dự đoán: {feedback.du_doan_score:.1f}/100\n"
        f"Đánh giá của người dùng: {feedback.thuc_te_score:.1f}/100\n"
        f"Scope: {prediction.scope}\n"
        f"Chỉ số tham khảo: {json.dumps(scores, ensure_ascii=False, sort_keys=True)}"
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {
                "role": "assistant",
                "content": json.dumps(analysis, ensure_ascii=False, separators=(",", ":")),
            },
        ]
    }


def _atomic_write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            for record in records:
                temp_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def build_dataset(
    db: Session, output_dir: Path, minimum_examples: int = 5
) -> dict[str, int]:
    if minimum_examples < 2:
        raise ValueError("minimum_examples must be at least two for a train/validation split.")

    rows = (
        db.query(EventFeedback, Prediction, Profile)
        .join(Prediction, EventFeedback.prediction_id == Prediction.id)
        .join(Profile, EventFeedback.profile_id == Profile.id)
        .join(User, Profile.user_id == User.id)
        .filter(
            User.training_consent.is_(True),
            EventFeedback.training_approved.is_(True),
            Prediction.profile_id == Profile.id,
            EventFeedback.scope == Prediction.scope,
            EventFeedback.scope_key.is_not_distinct_from(Prediction.scope_key),
        )
        .order_by(EventFeedback.id.asc())
        .all()
    )
    records: list[dict] = []
    skipped = 0
    for feedback, prediction, profile in rows:
        try:
            records.append(_training_record(feedback, prediction, profile))
        except (json.JSONDecodeError, TypeError, ValueError):
            skipped += 1

    if len(records) < minimum_examples:
        raise ValueError(
            f"Need at least {minimum_examples} approved, consented, privacy-safe "
            f"examples; found {len(records)}."
        )

    validation_count = max(1, round(len(records) * 0.2))
    validation = records[-validation_count:]
    training = records[:-validation_count]
    _atomic_write(output_dir / "train.jsonl", training)
    _atomic_write(output_dir / "validation.jsonl", validation)
    return {
        "examples": len(records),
        "train": len(training),
        "validation": len(validation),
        "skipped_for_privacy_or_format": skipped,
    }


def approve_feedback(db: Session, feedback_id: int) -> None:
    row = (
        db.query(EventFeedback, Profile, User)
        .join(Profile, EventFeedback.profile_id == Profile.id)
        .join(User, Profile.user_id == User.id)
        .filter(EventFeedback.id == feedback_id)
        .first()
    )
    if row is None:
        raise ValueError("Feedback not found.")
    feedback, _, user = row
    if feedback.prediction_id is None:
        raise ValueError("Feedback is not attached to an exact prediction.")
    prediction = (
        db.query(Prediction)
        .filter_by(id=feedback.prediction_id, profile_id=feedback.profile_id)
        .first()
    )
    if prediction is None:
        raise ValueError("Feedback prediction does not belong to its profile.")
    if (
        feedback.scope != prediction.scope
        or feedback.scope_key != prediction.scope_key
    ):
        raise ValueError("Feedback scope does not match its linked prediction.")
    if not user.training_consent:
        raise ValueError("The user has not opted in to dataset use.")
    feedback.training_approved = True
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approve-feedback-id",
        type=int,
        action="append",
        default=[],
        help="Explicitly approve a linked feedback row after human review (repeatable).",
    )
    parser.add_argument("--minimum-examples", type=int, default=5)
    args = parser.parse_args()
    output_dir = Path(
        os.getenv(
            "HUYEN_HOC_DATASET_DIR",
            str(Path(__file__).resolve().parent.parent / "finetune" / "dataset"),
        )
    ).expanduser().resolve()

    with SessionLocal() as db:
        for feedback_id in args.approve_feedback_id:
            approve_feedback(db, feedback_id)
        counts = build_dataset(db, output_dir, args.minimum_examples)
    print(json.dumps({"output_dir": str(output_dir), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
