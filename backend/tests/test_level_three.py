import json
import os
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ab_testing import (
    assign_variant,
    experiment_metrics,
    record_experiment,
    record_feedback_reward,
    update_weights,
)
from database import (
    ABReward,
    Base,
    EventFeedback,
    Prediction,
    Profile,
    User,
    utcnow_naive,
)
from kinh_dich import KING_WEN, TRIGRAM_ORDER, _NUMBER_BY_TRIGRAMS, gieo_que
from social import compatibility, create_share_link, get_share_link, revoke_share_link
from tarot import _deck, draw_cards
from tu_vi import lap_la_so


class TarotAndIChingTests(unittest.TestCase):
    def test_tarot_deck_and_spreads_have_unique_cards_and_valid_positions(self) -> None:
        deck = _deck()
        self.assertEqual(len(deck), 78)
        self.assertEqual(len({card["id"] for card in deck}), 78)
        for count in (1, 3, 5):
            cards = draw_cards(count)
            self.assertEqual(len(cards), count)
            self.assertEqual(len({card["id"] for card in cards}), count)
            self.assertTrue(all(isinstance(card["reversed"], bool) for card in cards))
            self.assertEqual(len({card["vi_tri"] for card in cards}), count)
        with self.assertRaises(ValueError):
            draw_cards(2)

    def test_king_wen_map_is_complete_unique_and_oriented_upper_then_lower(self) -> None:
        numbers = [number for row in KING_WEN for number in row]
        self.assertEqual(sorted(numbers), list(range(1, 65)))
        self.assertEqual(len(_NUMBER_BY_TRIGRAMS), 64)
        self.assertEqual(
            _NUMBER_BY_TRIGRAMS[("Càn", "Đoài")],
            10,
        )
        self.assertEqual(_NUMBER_BY_TRIGRAMS[("Đoài", "Càn")], 43)
        self.assertEqual(len(TRIGRAM_ORDER), 8)
        cast = gieo_que()
        self.assertEqual(len(cast["que_chinh"]["hao"]), 6)
        self.assertTrue(1 <= cast["que_chinh"]["so"] <= 64)
        self.assertTrue(
            cast["que_bien"] is None or 1 <= cast["que_bien"]["so"] <= 64
        )


class SocialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(username="share-user", email="share@example.test", hashed_password="x")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_share_token_is_only_stored_as_digest_and_can_be_revoked(self) -> None:
        token, row = create_share_link(self.db, self.user.id, {"con_giap": "Hợi"})
        self.assertNotEqual(row.token_digest, token)
        self.assertIsNotNone(get_share_link(self.db, token))
        self.assertTrue(revoke_share_link(self.db, self.user.id, token))
        self.assertIsNone(get_share_link(self.db, token))

    def test_expired_share_is_unavailable(self) -> None:
        token, row = create_share_link(self.db, self.user.id, {"con_giap": "Hợi"})
        row.expires_at = utcnow_naive() - timedelta(seconds=1)
        self.db.commit()
        self.assertIsNone(get_share_link(self.db, token))

    def test_compatibility_output_is_explanatory_and_limited(self) -> None:
        result = compatibility(15, 6, 1995, 4, 9, 1997)
        self.assertIn("diem_tham_khao", result)
        self.assertIn("cac_yeu_to", result)
        self.assertTrue(0 <= result["diem_tham_khao"] <= 100)
        self.assertNotIn("ngay_sinh", json.dumps(result, ensure_ascii=False))


class ABTestingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(username="ab-user", email="ab@example.test", hashed_password="x")
        self.db.add(self.user)
        self.db.flush()
        self.profile = Profile(
            user_id=self.user.id,
            ngay_sinh="15/06/1995",
            profile_json="{}",
        )
        self.db.add(self.profile)
        self.db.flush()
        self.prediction = Prediction(
            profile_id=self.profile.id,
            chi_so_json="{}",
            du_doan_json="{}",
        )
        self.db.add(self.prediction)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_assignment_is_sticky_and_weight_change_affects_new_users(self) -> None:
        first = assign_variant(self.db, self.user.id, "analyze")
        self.assertIn(first, ("control", "treatment"))
        self.assertEqual(assign_variant(self.db, self.user.id, "analyze"), first)
        update_weights(self.db, "analyze", {"control": 0.0, "treatment": 1.0})
        other = User(username="ab-user-2", email="ab2@example.test", hashed_password="x")
        self.db.add(other)
        self.db.commit()
        self.assertEqual(assign_variant(self.db, other.id, "analyze"), "treatment")

    def test_reward_uses_exact_linked_prediction_and_metrics_are_user_scoped(self) -> None:
        experiment = record_experiment(
            self.db, self.user.id, self.prediction.id, "analyze", "control", 100, True
        )
        feedback = EventFeedback(
            profile_id=self.profile.id,
            prediction_id=self.prediction.id,
            loai_su_kien="tai_van",
            du_doan_score=80,
            thuc_te_score=90,
        )
        self.db.add(feedback)
        self.db.flush()
        reward = record_feedback_reward(self.db, feedback, self.profile)
        self.db.commit()
        self.assertEqual(reward.experiment_id, experiment.id)
        self.assertAlmostEqual(reward.reward, 0.9)
        self.assertEqual(self.db.query(ABReward).count(), 1)
        metrics = experiment_metrics(self.db, self.user.id)["experiments"]
        self.assertEqual(metrics[0]["feedback_count"], 1)
        self.assertAlmostEqual(metrics[0]["mean_reward"], 0.9)


class LevelThreeAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        with self.factory() as db:
            self.user = User(
                username="api-user",
                email="api-user@example.test",
                hashed_password="x",
            )
            db.add(self.user)
            db.commit()
            db.refresh(self.user)

        from main import app
        from database import get_db
        from auth import get_current_user

        def override_db():
            with self.factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.app = app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()

    def test_authenticated_share_omits_birth_date_and_supports_revoke(self) -> None:
        with self.factory() as db:
            db.add(Profile(
                user_id=self.user.id,
                ngay_sinh="15/06/1995",
                ho_ten="Private User",
                profile_json=json.dumps({
                    "ngay_sinh": "15/06/1995",
                    "ho_ten": "Private User",
                    "menh_nap_am": "Hỏa",
                    "can_chi_nam": "Ất Hợi",
                    "con_giap": "Hợi",
                    "so_chu_dao": 9,
                    "cung_phi": 8,
                }),
            ))
            db.commit()
        response = self.client.post(
            "/api/share",
            json={"ngay_sinh": "1995-06-15", "expires_in_days": 7},
        )
        self.assertEqual(response.status_code, 200)
        share_url = response.json()["url"]
        token = share_url.rsplit("/", 1)[1]
        shared = self.client.get(share_url.replace("/share/", "/api/share/"))
        self.assertEqual(shared.status_code, 200)
        serialized = json.dumps(shared.json(), ensure_ascii=False)
        self.assertNotIn("15/06/1995", serialized)
        self.assertNotIn("Private User", serialized)
        self.assertEqual(
            self.client.delete(share_url.replace("/share/", "/api/share/")).status_code,
            200,
        )
        self.assertEqual(self.client.get(f"/api/share/{token}").status_code, 404)

    def test_saved_profiles_and_latest_interpretation_are_user_scoped(self) -> None:
        profile_data = {
            "ho_ten": "Người thử nghiệm",
            "ngay_sinh": "15/06/1995",
            "con_giap": "Hợi",
        }
        with self.factory() as db:
            profile = Profile(
                user_id=self.user.id,
                ngay_sinh=profile_data["ngay_sinh"],
                ho_ten=profile_data["ho_ten"],
                profile_json=json.dumps(profile_data, ensure_ascii=False),
            )
            other_user = User(
                username="other-saved-profile",
                email="other-saved-profile@example.test",
                hashed_password="x",
            )
            db.add_all([profile, other_user])
            db.commit()
            db.refresh(profile)
            db.add(Prediction(
                profile_id=profile.id,
                chi_so_json='{"tai_van": 55}',
                du_doan_json='{"tom_tat":"Kết quả đã lưu"}',
            ))
            other_profile = Profile(
                user_id=other_user.id,
                ngay_sinh="01/01/2000",
                ho_ten="Không được lộ",
                profile_json="{}",
            )
            db.add(other_profile)
            db.commit()

        response = self.client.get("/api/profiles")
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["profile"]["ho_ten"], "Người thử nghiệm")
        self.assertEqual(
            items[0]["latest_prediction"]["phan_tich"]["tom_tat"],
            "Kết quả đã lưu",
        )

    def test_analysis_preferences_and_telegram_result_delivery_are_opt_in(self) -> None:
        with self.factory() as db:
            user = db.get(User, self.user.id)
            user.telegram_chat_id = 123456
            db.commit()
        self.user.telegram_chat_id = 123456
        preferences = self.client.put(
            "/api/auth/preferences",
            json={
                "training_consent": False,
                "notifications_enabled": False,
                "analysis_notifications_enabled": True,
            },
        )
        self.assertEqual(preferences.status_code, 200)
        self.assertTrue(preferences.json()["analysis_notifications_enabled"])
        self.user.analysis_notifications_enabled = True

        async def fake_stream(prompt, system, temperature, json_mode):
            del prompt, system, temperature, json_mode
            yield {
                "token": '{"tom_tat":"Kết quả thử","diem_manh":[]}',
                "done": True,
            }

        from main import ollama
        with patch.object(ollama, "generate_stream", fake_stream):
            with patch(
                "notifications.telegram.send_document",
                new_callable=AsyncMock,
            ) as send_document:
                response = self.client.post(
                    "/api/analyze/stream",
                    json={"ho_ten": "Người thử", "ngay": 15, "thang": 6, "nam": 1995},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"telegram_notification":"sent"', response.text)
        send_document.assert_awaited_once()
        sent_content = send_document.await_args.args[2]
        self.assertIn("Kết quả thử", sent_content.decode("utf-8"))
        self.assertIn("Người thử", sent_content.decode("utf-8"))

    def test_compatibility_validates_and_returns_result(self) -> None:
        response = self.client.post(
            "/api/hop-tuoi",
            json={"ngay_sinh_a": "1995-06-15", "ngay_sinh_b": "1997-09-04"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("diem_tham_khao", response.json())
        invalid = self.client.post(
            "/api/hop-tuoi",
            json={"ngay_sinh_a": "1995-02-30", "ngay_sinh_b": "1997-09-04"},
        )
        self.assertEqual(invalid.status_code, 422)

    def test_share_chart_requires_saved_chart_and_filters_birth_fields(self) -> None:
        with self.factory() as db:
            profile = Profile(
                user_id=self.user.id,
                ngay_sinh="15/06/1995",
                profile_json=json.dumps({
                    "menh_nap_am": "Hỏa",
                    "can_chi_nam": "Ất Hợi",
                    "con_giap": "Hợi",
                    "so_chu_dao": 9,
                    "cung_phi": 8,
                }),
            )
            db.add(profile)
            db.commit()
        response = self.client.post(
            "/api/share",
            json={"ngay_sinh": "1995-06-15", "include_chart": True},
        )
        self.assertEqual(response.status_code, 409)
        with self.factory() as db:
            profile = db.query(Profile).filter_by(user_id=self.user.id).one()
            profile.tu_vi_json = json.dumps(lap_la_so(15, 6, 1995, 10), ensure_ascii=False)
            db.commit()
        response = self.client.post(
            "/api/share",
            json={"ngay_sinh": "1995-06-15", "include_chart": True},
        )
        self.assertEqual(response.status_code, 200)
        payload = self.client.get(
            response.json()["url"].replace("/share/", "/api/share/")
        ).json()["profile"]
        encoded = json.dumps(payload, ensure_ascii=False)
        for private_key in ('"ngay_sinh"', '"duong_lich"', '"am_lich"', '"gio_sinh"'):
            self.assertNotIn(private_key, encoded)
        self.assertEqual(len(payload["la_so"]["cung"]), 12)

    def test_tarot_and_iching_routes_return_safe_results(self) -> None:
        with patch("main.luan_giai_tarot", new=AsyncMock(return_value={"cards": []})):
            tarot = self.client.post("/api/tarot", json={"cau_hoi": "Tôi nên suy ngẫm gì?"})
        with patch("main.luan_giai_que", new=AsyncMock(return_value={"que_chinh": {"so": 1}})):
            iching = self.client.post("/api/kinh-dich", json={"cau_hoi": "Tôi nên suy ngẫm gì?"})
        self.assertEqual(tarot.status_code, 200)
        self.assertEqual(iching.json()["que_chinh"]["so"], 1)
        self.assertEqual(
            self.client.post("/api/tarot", json={"cau_hoi": "ok", "so_la": 9}).status_code,
            422,
        )

    def test_pdf_route_returns_pdf_and_rejects_unauthenticated_access(self) -> None:
        with patch("main.export_la_so_pdf", return_value=b"%PDF-test"):
            response = self.client.post(
                "/api/tu-vi/export-pdf",
                json={"ngay": 15, "thang": 6, "nam": 1995},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-test")

    def test_ab_analysis_and_feedback_are_linked_to_same_prediction(self) -> None:
        with patch(
            "main.ollama.generate",
            new=AsyncMock(return_value='{"tom_tat":"Tham khảo","hanh_dong_cu_the":[]}'),
        ):
            response = self.client.post(
                "/api/analyze/ab",
                json={"ho_ten": "", "ngay": 15, "thang": 6, "nam": 1995},
            )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn(result["variant"], ("control", "treatment"))
        feedback_response = self.client.post(
            "/api/feedback",
            json={
                "ngay_sinh": "15/06/1995",
                "prediction_id": result["prediction_id"],
                "loai_su_kien": "tai_van",
                "du_doan_score": 50,
                "thuc_te_score": 60,
            },
        )
        self.assertEqual(feedback_response.status_code, 200)
        with self.factory() as db:
            metrics = experiment_metrics(db, self.user.id)
            self.assertEqual(metrics["experiments"][0]["feedback_count"], 1)
            self.assertEqual(
                db.query(ABReward).count(),
                1,
            )

    def test_ab_weight_updates_require_configured_user_id(self) -> None:
        request = {"task": "analyze", "weights": {"control": 1, "treatment": 3}}
        with patch.dict(os.environ, {"ADMIN_USER_IDS": ""}):
            forbidden = self.client.put("/api/admin/ab/weights", json=request)
        self.assertEqual(forbidden.status_code, 403)
        with patch.dict(os.environ, {"ADMIN_USER_IDS": str(self.user.id)}):
            allowed = self.client.put("/api/admin/ab/weights", json=request)
            invalid = self.client.put(
                "/api/admin/ab/weights",
                json={"task": "analyze", "weights": {"custom": 1}},
            )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["weights"], {"control": 0.25, "treatment": 0.75})
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
