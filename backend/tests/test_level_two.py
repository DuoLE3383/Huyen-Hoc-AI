import hashlib
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from database import (
    Base,
    EventFeedback,
    Prediction,
    Profile,
    TelegramLinkChallenge,
    User,
    utcnow_naive,
)
from dataset_builder import approve_feedback, build_dataset
from notifications import handle_command
from ollama_client import OllamaClient


class StreamingClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_stream_decodes_ndjson_chunks(self) -> None:
        def response(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/generate")
            payload = json.loads(request.content)
            self.assertTrue(payload["stream"])
            self.assertEqual(payload["options"]["num_ctx"], 8192)
            return httpx.Response(
                200,
                content=(
                    b'{"response":"xin ","done":false}\n'
                    b'{"response":"chao","done":true}\n'
                ),
            )

        client = OllamaClient(transport=httpx.MockTransport(response))
        self.assertEqual(client.num_ctx, 8192)
        chunks = [chunk async for chunk in client.generate_stream("prompt")]
        self.assertEqual(chunks, [
            {"token": "xin ", "done": False},
            {"token": "chao", "done": True},
        ])

    async def test_generate_stream_rejects_malformed_chunk(self) -> None:
        def malformed_response(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/generate")
            return httpx.Response(200, content=b"not-json\n")

        client = OllamaClient(transport=httpx.MockTransport(malformed_response))
        with self.assertRaises(ValueError):
            _ = [chunk async for chunk in client.generate_stream("prompt")]

    async def test_generate_stream_rejects_unsafe_context_lengths(self) -> None:
        with self.assertRaises(ValueError):
            OllamaClient(num_ctx=262144)

    async def test_generate_stream_reads_error_body_before_raising(self) -> None:
        def error_response(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/generate")
            return httpx.Response(500, json={"error": "model runner terminated"})

        client = OllamaClient(transport=httpx.MockTransport(error_response))
        with self.assertRaises(httpx.HTTPStatusError) as raised:
            _ = [chunk async for chunk in client.generate_stream("prompt")]
        self.assertEqual(
            raised.exception.response.json(),
            {"error": "model runner terminated"},
        )


class LevelTwoDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        self.db = self.factory()
        self.user = User(
            username="opted-in",
            email="opted-in@example.test",
            hashed_password="hash",
            training_consent=True,
        )
        self.db.add(self.user)
        self.db.flush()
        self.profile = Profile(
            user_id=self.user.id,
            ngay_sinh="15/06/1995",
            ho_ten="Private Person",
            profile_json=json.dumps({
                "ngay_sinh": "15/06/1995",
                "ho_ten": "Private Person",
                "menh_nap_am": "Hỏa",
                "con_giap": "Hợi",
            }),
        )
        self.db.add(self.profile)
        self.db.flush()
        self.prediction = Prediction(
            profile_id=self.profile.id,
            scope="general",
            chi_so_json='{"tai_van": 50}',
            du_doan_json='{"tom_tat":"Hãy cân nhắc kế hoạch từng bước."}',
        )
        self.db.add(self.prediction)
        self.db.flush()
        self.feedback = EventFeedback(
            profile_id=self.profile.id,
            prediction_id=self.prediction.id,
            loai_su_kien="tai_van",
            du_doan_score=50,
            thuc_te_score=60,
        )
        self.db.add(self.feedback)
        self.second_feedback = EventFeedback(
            profile_id=self.profile.id,
            prediction_id=self.prediction.id,
            loai_su_kien="tai_van",
            du_doan_score=50,
            thuc_te_score=65,
        )
        self.db.add(self.second_feedback)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_dataset_requires_consent_approval_and_exact_prediction_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir)
            with self.assertRaisesRegex(ValueError, "at least two"):
                build_dataset(self.db, output, minimum_examples=1)
            with self.assertRaisesRegex(ValueError, "approved, consented"):
                build_dataset(self.db, output, minimum_examples=2)

            approve_feedback(self.db, self.feedback.id)
            approve_feedback(self.db, self.second_feedback.id)
            counts = build_dataset(self.db, output, minimum_examples=2)
            self.assertEqual(counts["examples"], 2)
            training = (output / "train.jsonl").read_text(encoding="utf-8")
            validation = (output / "validation.jsonl").read_text(encoding="utf-8")
            combined = training + validation
            self.assertIn("assistant", combined)
            self.assertNotIn("Private Person", combined)
            self.assertNotIn("15/06/1995", combined)

    def test_dataset_excludes_rows_after_consent_is_revoked(self) -> None:
        approve_feedback(self.db, self.feedback.id)
        self.user.training_consent = False
        self.db.commit()
        with tempfile.TemporaryDirectory() as temporary_dir:
            with self.assertRaisesRegex(ValueError, "approved, consented"):
                build_dataset(self.db, Path(temporary_dir), minimum_examples=2)

    def test_approval_rejects_unlinked_feedback(self) -> None:
        unlinked = EventFeedback(
            profile_id=self.profile.id,
            loai_su_kien="tai_van",
            du_doan_score=50,
            thuc_te_score=50,
        )
        self.db.add(unlinked)
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "exact prediction"):
            approve_feedback(self.db, unlinked.id)


class TelegramLinkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        self.db = self.factory()
        self.user = User(
            username="telegram-user",
            email="telegram-user@example.test",
            hashed_password="hash",
        )
        self.db.add(self.user)
        self.db.flush()
        self.challenge = TelegramLinkChallenge(
            user_id=self.user.id,
            code_digest=hashlib.sha256(b"valid-once-code").hexdigest(),
            expires_at=utcnow_naive() + timedelta(days=1),
        )
        self.db.add(self.challenge)
        self.db.commit()

    async def asyncTearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    async def test_one_time_code_links_existing_account_and_unlink_keeps_user(self) -> None:
        with patch("notifications.telegram.send_message", new_callable=AsyncMock):
            await handle_command(12345, "/link valid-once-code", self.db)
            await handle_command(12345, "/link valid-once-code", self.db)
            self.db.refresh(self.user)
            self.db.refresh(self.challenge)
            self.assertEqual(self.user.telegram_chat_id, 12345)
            self.assertFalse(self.user.notifications_enabled)
            self.assertIsNotNone(self.challenge.used_at)

            pending = TelegramLinkChallenge(
                user_id=self.user.id,
                code_digest=hashlib.sha256(b"pending-code").hexdigest(),
                expires_at=utcnow_naive() + timedelta(days=1),
            )
            pending_digest = pending.code_digest
            self.db.add(pending)
            self.db.commit()
            await handle_command(12345, "/unlink", self.db)
            self.db.refresh(self.user)
            self.assertIsNone(self.user.telegram_chat_id)
            self.assertFalse(self.user.notifications_enabled)
            self.assertIsNone(
                self.db.query(TelegramLinkChallenge)
                .filter_by(code_digest=pending_digest)
                .first()
            )
            self.assertIsNotNone(self.db.query(User).filter_by(id=self.user.id).first())

    async def test_invalid_link_does_not_create_or_link_an_account(self) -> None:
        with patch("notifications.telegram.send_message", new_callable=AsyncMock):
            await handle_command(54321, "/link wrong-code", self.db)
        self.assertIsNone(self.user.telegram_chat_id)
        self.assertEqual(self.db.query(User).count(), 1)


class StreamingEndpointTests(unittest.TestCase):
    def test_stream_error_includes_ollama_http_detail(self) -> None:
        import main

        response = httpx.Response(
            500,
            json={"error": "model runner has terminated"},
            request=httpx.Request("POST", "http://localhost:11434/api/generate"),
        )
        error = httpx.HTTPStatusError(
            "Server error", request=response.request, response=response
        )
        self.assertEqual(
            main._ollama_stream_error_message(error),
            "Ollama báo lỗi HTTP 500: model runner has terminated",
        )

    def test_stream_endpoint_emits_metadata_tokens_and_saved_result(self) -> None:
        import main

        from database import EventFeedback

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        db = factory()
        user = User(
            username="stream-user",
            email="stream-user@example.test",
            hashed_password="hash",
        )
        db.add(user)
        db.commit()

        def override_db():
            session = factory()
            try:
                yield session
            finally:
                session.close()

        async def fake_stream(prompt, system, temperature, json_mode):
            self.assertIn("Ngày sinh", prompt)
            self.assertTrue(system)
            self.assertEqual(temperature, 0.6)
            self.assertTrue(json_mode)
            yield {"token": '{"tom_tat":"Tham khảo",', "done": False}
            yield {"token": '"diem_manh":[]}', "done": True}

        main.app.dependency_overrides[main.get_db] = override_db
        main.app.dependency_overrides[main.get_current_user] = lambda: user
        try:
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": ""}):
                with patch.object(main.ollama, "generate_stream", fake_stream):
                    with TestClient(main.app) as client:
                        manifest = client.get("/manifest.json")
                        service_worker = client.get("/sw.js")
                        offline_page = client.get("/offline.html")
                        self.assertEqual(manifest.status_code, 200)
                        self.assertEqual(service_worker.status_code, 200)
                        self.assertEqual(
                            service_worker.headers["service-worker-allowed"], "/"
                        )
                        self.assertEqual(offline_page.status_code, 200)
                        response = client.post(
                            "/api/analyze/stream",
                            json={"ngay": 15, "thang": 6, "nam": 1995},
                        )
                        done_event = response.text.split("event: done\ndata: ", 1)[1]
                        done_data = json.loads(done_event.splitlines()[0])
                        feedback_response = client.post(
                            "/api/feedback",
                            json={
                                "ngay_sinh": "15/06/1995",
                                "prediction_id": done_data["prediction_id"],
                                "loai_su_kien": "tai_van",
                                "du_doan_score": 50,
                                "thuc_te_score": 60,
                            },
                        )
            self.assertEqual(response.status_code, 200)
            self.assertIn("event: metadata", response.text)
            self.assertIn("event: token", response.text)
            self.assertIn("event: done", response.text)
            self.assertEqual(feedback_response.status_code, 200)
            with factory() as check_db:
                self.assertEqual(check_db.query(Prediction).count(), 1)
                self.assertEqual(
                    check_db.query(EventFeedback).filter(
                        EventFeedback.prediction_id == done_data["prediction_id"]
                    ).count(),
                    1,
                )
        finally:
            main.app.dependency_overrides.clear()
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
