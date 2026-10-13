import os
import unittest
from datetime import date

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from analytics.analytics import accuracy_by_field, get_weights_from_history
from core.database import Base, EventFeedback, Profile, User, init_db, utcnow_naive
from divination.lich_van_nien import (
    du_doan_thang,
    du_doan_tuan,
    ngay_can_chi,
    quan_he_chi,
    tiet_khi_cua_ngay,
)
from divination.tu_vi import AmLich, CHINH_TINH, lap_la_so


class CalendarTests(unittest.TestCase):
    def test_weekly_llm_suggestions_are_normalized_for_the_frontend(self) -> None:
        from main import _normalize_weekly_text_list

        self.assertEqual(_normalize_weekly_text_list(["Lập kế hoạch"]), ["Lập kế hoạch"])
        self.assertEqual(_normalize_weekly_text_list("Nghỉ ngơi"), ["Nghỉ ngơi"])
        self.assertEqual(_normalize_weekly_text_list({"buổi sáng": "đi bộ"}), [
            '{"buổi sáng": "đi bộ"}'
        ])
        self.assertEqual(_normalize_weekly_text_list(None), [])

    def test_known_vietnamese_lunar_new_year_dates_and_leap_month(self) -> None:
        self.assertEqual(AmLich.solar_to_lunar(date(2023, 1, 22)), (1, 1, 2023, False))
        self.assertEqual(AmLich.solar_to_lunar(date(2024, 2, 10)), (1, 1, 2024, False))
        self.assertEqual(AmLich.solar_to_lunar(date(2023, 3, 22)), (1, 2, 2023, True))

    def test_day_cycle_and_season_term_year_wrap(self) -> None:
        self.assertEqual(ngay_can_chi(date(2000, 1, 1)), ("Mậu", "Ngọ"))
        self.assertEqual(tiet_khi_cua_ngay(date(2025, 1, 1)), "Đông Chí")
        self.assertEqual(tiet_khi_cua_ngay(date(2025, 2, 4)), "Lập Xuân")
        self.assertIn("xung", quan_he_chi("Tý", "Ngọ"))
        self.assertIn("hại", quan_he_chi("Tý", "Mùi"))
        self.assertIn("tự hình", quan_he_chi("Thìn", "Thìn"))
        self.assertEqual(quan_he_chi("Tý", "Tý"), ["bình hòa"])

    def test_week_month_and_chart_have_expected_shape(self) -> None:
        week = du_doan_tuan("Kim", "Tý", date(2025, 1, 1))
        month = du_doan_thang("Kim", "Tý", 2024, 2)
        chart = lap_la_so(15, 6, 1995, 10)
        self.assertEqual(len(week), 7)
        self.assertEqual(len(month), 29)
        self.assertEqual(len(chart["cung"]), 12)
        chart_stars = [
            star["sao"] for palace in chart["cung"] for star in palace["chinh_tinh"]
        ]
        self.assertCountEqual(chart_stars, CHINH_TINH)
        self.assertTrue(all(0 <= palace["vi_tri"] < 12 for palace in chart["cung"]))


class AnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        user = User(username="tester", email="test@example.com", hashed_password="hash")
        self.session.add(user)
        self.session.flush()
        profile = Profile(
            user_id=user.id,
            ngay_sinh="01/01/2000",
            profile_json="{}",
        )
        self.session.add(profile)
        self.session.flush()
        self.profile_id = profile.id

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_accuracy_and_sparse_feedback_weights(self) -> None:
        for _ in range(5):
            self.session.add(EventFeedback(
                profile_id=self.profile_id,
                loai_su_kien="tai_van",
                du_doan_score=80,
                thuc_te_score=70,
                created_at=utcnow_naive(),
            ))
        self.session.commit()
        metrics = accuracy_by_field(self.session, [self.profile_id])
        weights = get_weights_from_history(self.session, [self.profile_id])
        self.assertEqual(metrics["tong_feedback"], 5)
        self.assertEqual(metrics["fields"][0]["mae"], 10)
        self.assertEqual(weights["tai_van"], 1.4)
        self.assertEqual(weights["tinh_duyen"], 1.0)

    def test_multi_user_can_have_same_birth_date(self) -> None:
        second = User(username="other", email="other@example.com", hashed_password="hash")
        self.session.add(second)
        self.session.flush()
        self.session.add(Profile(
            user_id=second.id,
            ngay_sinh="01/01/2000",
            profile_json="{}",
        ))
        self.session.commit()
        profiles = self.session.query(Profile).filter_by(ngay_sinh="01/01/2000").all()
        self.assertEqual(len(profiles), 2)


class DatabaseMigrationTests(unittest.TestCase):
    def test_legacy_schema_is_migrated_for_multi_user(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE profiles (id INTEGER PRIMARY KEY, ngay_sinh VARCHAR "
                "UNIQUE, ho_ten VARCHAR, profile_json TEXT, created_at DATETIME)"
            ))
            connection.execute(text(
                "CREATE UNIQUE INDEX ix_profiles_ngay_sinh ON profiles (ngay_sinh)"
            ))
            connection.execute(text(
                "CREATE TABLE predictions (id INTEGER PRIMARY KEY, profile_id INTEGER, "
                "chi_so_json TEXT, du_doan_json TEXT, created_at DATETIME)"
            ))
            connection.execute(text(
                "CREATE TABLE event_feedback (id INTEGER PRIMARY KEY, profile_id INTEGER, "
                "loai_su_kien VARCHAR, du_doan_score FLOAT, thuc_te_score FLOAT, "
                "ghi_chu TEXT, created_at DATETIME)"
            ))
        init_db(engine)
        inspector = inspect(engine)
        profile_columns = {column["name"] for column in inspector.get_columns("profiles")}
        prediction_columns = {column["name"] for column in inspector.get_columns("predictions")}
        feedback_columns = {column["name"] for column in inspector.get_columns("event_feedback")}
        self.assertIn("user_id", profile_columns)
        self.assertIn("tu_vi_json", profile_columns)
        self.assertIn("scope_key", prediction_columns)
        self.assertIn("scope", feedback_columns)
        self.assertIn("prediction_id", feedback_columns)
        self.assertIn("training_approved", feedback_columns)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        self.assertIn("telegram_chat_id", user_columns)
        self.assertIn("notifications_enabled", user_columns)
        self.assertIn("analysis_notifications_enabled", user_columns)
        self.assertIn("training_consent", user_columns)

        factory = sessionmaker(bind=engine)
        with factory() as session:
            users = [
                User(username="first", email="first@example.com", hashed_password="hash"),
                User(username="second", email="second@example.com", hashed_password="hash"),
            ]
            session.add_all(users)
            session.flush()
            session.add_all([
                Profile(user_id=user.id, ngay_sinh="01/01/2000", profile_json="{}")
                for user in users
            ])
            session.commit()
            self.assertEqual(session.query(Profile).count(), 2)
        engine.dispose()


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_verification_and_token_configuration(self) -> None:
        from core.auth import create_access_token, hash_password, verify_password

        password = "strong-test-password"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("different-password", hashed))
        previous = os.environ.get("HUYEN_HOC_SECRET_KEY")
        os.environ["HUYEN_HOC_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        try:
            self.assertIsInstance(create_access_token({"sub": "1"}), str)
        finally:
            if previous is None:
                os.environ.pop("HUYEN_HOC_SECRET_KEY", None)
            else:
                os.environ["HUYEN_HOC_SECRET_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
