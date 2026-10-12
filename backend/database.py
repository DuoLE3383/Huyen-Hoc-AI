from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.engine import Engine

DATABASE_URL = os.getenv(
    "HUYEN_HOC_DATABASE_URL",
    f"sqlite:///{(Path(__file__).resolve().parent / 'huyen_hoc.db').as_posix()}",
)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_telegram_chat_id", "telegram_chat_id", unique=True),)

    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, index=True, nullable=False)
    email = Column(String(254), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), default="", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_chat_id = Column(Integer, nullable=True)
    notifications_enabled = Column(Boolean, default=False, nullable=False)
    analysis_notifications_enabled = Column(Boolean, default=False, nullable=False)
    training_consent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    profiles = relationship("Profile", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    ngay_sinh = Column(String(10), index=True, nullable=False)
    ho_ten = Column(String(100), nullable=True)
    profile_json = Column(Text, nullable=False)
    tu_vi_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    user = relationship("User", back_populates="profiles")
    __table_args__ = (Index("uq_profiles_user_birth", "user_id", "ngay_sinh", unique=True),)


class SavedEvent(Base):
    __tablename__ = "saved_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    loai = Column(String(32), nullable=False)
    ngay = Column(String(10), nullable=False, index=True)
    ghi_chu = Column(String(500), default="", nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), index=True, nullable=False)
    scope = Column(String(20), default="general", nullable=False)
    scope_key = Column(String(20), nullable=True)
    chi_so_json = Column(Text, nullable=False)
    du_doan_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class TelegramLinkChallenge(Base):
    __tablename__ = "telegram_link_challenges"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    code_digest = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class TelegramPollingState(Base):
    __tablename__ = "telegram_polling_state"

    id = Column(Integer, primary_key=True)
    next_update_id = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=utcnow_naive, nullable=False)


class EventFeedback(Base):
    __tablename__ = "event_feedback"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), index=True, nullable=False)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), index=True, nullable=True)
    loai_su_kien = Column(String(32), nullable=False)
    du_doan_score = Column(Float, nullable=False)
    thuc_te_score = Column(Float, nullable=False)
    ghi_chu = Column(Text, nullable=True)
    scope = Column(String(20), default="general", nullable=False)
    scope_key = Column(String(20), nullable=True)
    training_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class ShareLink(Base):
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    token_digest = Column(String(64), unique=True, nullable=False)
    payload_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class ABAssignment(Base):
    __tablename__ = "ab_assignments"
    __table_args__ = (Index("uq_ab_assignment_user_task", "user_id", "task", unique=True),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    task = Column(String(32), nullable=False)
    variant = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class ABExperiment(Base):
    __tablename__ = "ab_experiments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), unique=True, nullable=True)
    task = Column(String(32), nullable=False, index=True)
    variant = Column(String(32), nullable=False, index=True)
    latency_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class ABVariantWeight(Base):
    __tablename__ = "ab_variant_weights"
    __table_args__ = (Index("uq_ab_variant_task_name", "task", "variant", unique=True),)

    id = Column(Integer, primary_key=True)
    task = Column(String(32), nullable=False)
    variant = Column(String(32), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    updated_at = Column(DateTime, default=utcnow_naive, nullable=False)


class ABReward(Base):
    __tablename__ = "ab_rewards"
    __table_args__ = (Index("uq_ab_reward_experiment_feedback", "experiment_id", "feedback_id", unique=True),)

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("ab_experiments.id"), index=True, nullable=False)
    feedback_id = Column(Integer, ForeignKey("event_feedback.id"), nullable=False)
    reward = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_columns(connection, table: str, columns: dict[str, str]) -> None:
    existing = {column["name"] for column in inspect(connection).get_columns(table)}
    for name, declaration in columns.items():
        if name not in existing:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"))


def _remove_legacy_birth_uniqueness(connection) -> None:
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("profiles")}
    unique_birth = any(
        constraint.get("column_names") == ["ngay_sinh"]
        for constraint in inspector.get_unique_constraints("profiles")
    ) or any(
        index.get("unique") and index.get("column_names") == ["ngay_sinh"]
        for index in inspector.get_indexes("profiles")
    )
    if not unique_birth:
        return

    connection.execute(text(
        "CREATE TABLE __profiles_multiuser ("
        "id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), "
        "ngay_sinh VARCHAR(10) NOT NULL, ho_ten VARCHAR(100), "
        "profile_json TEXT NOT NULL, tu_vi_json TEXT, created_at DATETIME NOT NULL)"
    ))
    user_id = "user_id" if "user_id" in columns else "NULL"
    tu_vi_json = "tu_vi_json" if "tu_vi_json" in columns else "NULL"
    connection.execute(text(
        "INSERT INTO __profiles_multiuser "
        "(id, user_id, ngay_sinh, ho_ten, profile_json, tu_vi_json, created_at) "
        f"SELECT id, {user_id}, ngay_sinh, ho_ten, profile_json, {tu_vi_json}, created_at "
        "FROM profiles"
    ))
    connection.execute(text("DROP TABLE profiles"))
    connection.execute(text("ALTER TABLE __profiles_multiuser RENAME TO profiles"))


def init_db(database_engine: Engine = engine) -> None:
    User.__table__.create(bind=database_engine, checkfirst=True)
    with database_engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        if "users" in tables:
            _add_missing_columns(
                connection,
                "users",
                {
                    "telegram_chat_id": "INTEGER",
                    "notifications_enabled": "BOOLEAN NOT NULL DEFAULT 0",
                    "analysis_notifications_enabled": "BOOLEAN NOT NULL DEFAULT 0",
                    "training_consent": "BOOLEAN NOT NULL DEFAULT 0",
                },
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_telegram_chat_id "
                    "ON users (telegram_chat_id)"
                )
            )
        if "profiles" in tables:
            _remove_legacy_birth_uniqueness(connection)
            _add_missing_columns(
                connection,
                "profiles",
                {
                    "user_id": "INTEGER REFERENCES users(id)",
                    "tu_vi_json": "TEXT",
                },
            )
            connection.execute(text("DROP INDEX IF EXISTS ix_profiles_ngay_sinh"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_user_birth "
                    "ON profiles (user_id, ngay_sinh)"
                )
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_profiles_user_id ON profiles (user_id)")
            )
        if "predictions" in tables:
            _add_missing_columns(
                connection, "predictions", {"scope": "VARCHAR(20) NOT NULL DEFAULT 'general'", "scope_key": "VARCHAR(20)"}
            )
        if "event_feedback" in tables:
            _add_missing_columns(
                connection, "event_feedback", {"scope": "VARCHAR(20) NOT NULL DEFAULT 'general'", "scope_key": "VARCHAR(20)"}
            )
            _add_missing_columns(
                connection,
                "event_feedback",
                {
                    "prediction_id": "INTEGER REFERENCES predictions(id)",
                    "training_approved": "BOOLEAN NOT NULL DEFAULT 0",
                },
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_event_feedback_prediction_id "
                    "ON event_feedback (prediction_id)"
                )
            )
    Base.metadata.create_all(bind=database_engine)
