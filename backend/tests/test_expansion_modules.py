import asyncio
import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ket_noi import buc_tranh_tong_the
from moi_truong import WeatherProviderError, lay_du_lieu_moi_truong
from phong_thuy import hop_huong_nha, phan_tich_toan_dien, tinh_cung_phi_gioi_tinh
from ban_do_phong_thuy import phan_tich_dia_hinh, phuong_vi_tu_hai_diem
from gia_dao import phan_tich_nhom_gia_dinh
from kinh_te_vi_mo import lay_ty_gia_usd_vnd, lay_vn_index
from tam_linh import tao_thoi_khoa_tam_linh
from trach_cat import tim_ngay_dep
from tu_vi_tay_phuong import lap_natal_chart
from su_kien import quet_su_kien_tuan
from vi_mo import timeline_vi_mo


class ExpansionModuleTests(unittest.TestCase):
    def test_kua_number_uses_gender_and_birth_year(self) -> None:
        self.assertEqual(tinh_cung_phi_gioi_tinh(1, 1, 1990, "nam"), 1)
        self.assertEqual(tinh_cung_phi_gioi_tinh(1, 1, 1990, "nu"), 8)
        self.assertEqual(tinh_cung_phi_gioi_tinh(1, 1, 2000, "nam"), 9)
        with self.assertRaises(ValueError):
            tinh_cung_phi_gioi_tinh(31, 2, 1990, "nam")

    def test_house_direction_rejects_invalid_values(self) -> None:
        self.assertTrue(hop_huong_nha(1, "Đông Nam")["tot"])
        self.assertIn("ghi_chu", phan_tich_toan_dien(15, 6, 1995))
        with self.assertRaises(ValueError):
            hop_huong_nha(1, "Đông Tây")

    def test_week_event_scan_filters_and_orders_supplied_events(self) -> None:
        result = quet_su_kien_tuan([
            {"id": 2, "loai": "ky_hop_dong", "ngay": "2025-05-04", "note": ""},
            {"id": 3, "loai": "thi_cu", "ngay": "2025-05-12", "note": ""},
            {"id": 1, "loai": "sinh_nhat", "ngay": "2025-05-01", "note": ""},
        ], date(2025, 5, 1))
        self.assertEqual(result["tong_su_kien"], 2)
        self.assertEqual([event["id"] for event in result["su_kien"]], [1, 2])
        self.assertIn("không phải xác suất", result["ghi_chu"])

    def test_macro_timeline_marks_approximate_solar_term(self) -> None:
        result = timeline_vi_mo(date(2025, 2, 1), 5)
        self.assertEqual(result["den_ngay"], "2025-02-05")
        self.assertIn("Lập Xuân", [event["ten"] for event in result["su_kien"]])
        self.assertIn("xấp xỉ", result["ghi_chu"])

    def test_environment_provider_requires_server_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(WeatherProviderError, "OPENWEATHER_API_KEY"):
                asyncio.run(lay_du_lieu_moi_truong(0, 0))

    def test_combined_summary_does_not_claim_prediction(self) -> None:
        result = buc_tranh_tong_the(
            {"menh_nap_am": "Mộc", "con_giap": "Mão"},
            {"cung_phi": 4, "quai": "Tốn", "huong_nha": {"huong_nha": "Nam", "cung": "Thiên Y"}},
            {"tu_ngay": "2025-05-01", "den_ngay": "2025-05-07", "su_kien": []},
        )
        self.assertEqual(len(result["cac_yeu_to"]), 2)
        self.assertIn("không phải dự báo", result["ghi_chu"])

    def test_location_requires_two_points_for_bearing(self) -> None:
        self.assertEqual(phan_tich_dia_hinh(None)["do_cao_m"], None)
        self.assertEqual(
            phuong_vi_tu_hai_diem(21.0, 105.0, 22.0, 105.0)["huong"], "Bắc"
        )
        with self.assertRaises(ValueError):
            phuong_vi_tu_hai_diem(91.0, 0, 0, 0)

    def test_family_summary_does_not_echo_birth_dates_or_score_relationships(self) -> None:
        result = phan_tich_nhom_gia_dinh([
            {"ten": "A", "vai_tro": "bố", "cung_phi": 1},
            {"ten": "B", "vai_tro": "mẹ", "cung_phi": 8},
        ])
        self.assertEqual(result["so_thanh_vien"], 2)
        self.assertNotIn("ngay_sinh", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("diem", result)

    def test_date_picker_is_bounded_and_disclaims_prediction(self) -> None:
        result = tim_ngay_dep("gap_go", date(2025, 5, 1), 10, 3)
        self.assertEqual(result["so_ngay_tim"], 10)
        self.assertLessEqual(len(result["top_ngay_tham_khao"]), 3)
        self.assertIn("không dự báo", result["ghi_chu"])
        with self.assertRaises(ValueError):
            tim_ngay_dep("gap_go", date.today(), 91)

    def test_mindfulness_and_western_chart_avoid_diagnosis_or_fabricated_positions(self) -> None:
        mindfulness = tao_thoi_khoa_tam_linh()
        self.assertIn("không chẩn đoán", mindfulness["ghi_chu"])
        chart = lap_natal_chart(15, 6, 1995)
        self.assertEqual(chart["mat_troi"]["ten"], "Gemini")
        self.assertIsNone(chart["cung_moc"])
        self.assertIsNone(chart["mat_trang"])

    def test_market_adapters_parse_mocked_public_data(self) -> None:
        timestamp = int(datetime(2025, 5, 1, tzinfo=timezone.utc).timestamp())

        async def handler(request: httpx.Request) -> httpx.Response:
            if "yahoo" in request.url.host:
                return httpx.Response(200, json={
                    "chart": {"result": [{
                        "timestamp": [timestamp],
                        "indicators": {"quote": [{"close": [1234.5]}]},
                    }]}
                })
            return httpx.Response(200, json={"date": "2025-05-01", "rates": {"VND": 25000}})

        async def run_adapters() -> tuple[dict, dict]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await asyncio.gather(
                    lay_vn_index(client), lay_ty_gia_usd_vnd(client)
                )

        vn_index, fx = asyncio.run(run_adapters())
        self.assertEqual(vn_index["gia_tri"], 1234.5)
        self.assertEqual(fx["usd_vnd"], 25000.0)


class ExpansionAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from database import Base, User, get_db
        from auth import get_current_user

        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        with self.factory() as db:
            self.user = User(username="event-owner", email="event-owner@example.test", hashed_password="x")
            self.other_user = User(username="event-other", email="event-other@example.test", hashed_password="x")
            db.add_all([self.user, self.other_user])
            db.commit()
            db.refresh(self.user)
            db.refresh(self.other_user)

        from main import app

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

    def test_saved_events_are_private_and_combined_route_is_available(self) -> None:
        created = self.client.post(
            "/api/su-kien",
            json={"loai": "ky_hop_dong", "ngay": date.today().isoformat(), "ghi_chu": "Rà soát điều khoản"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        event_id = created.json()["id"]

        from auth import get_current_user
        self.app.dependency_overrides[get_current_user] = lambda: self.other_user
        self.assertEqual(self.client.get("/api/su-kien").json()["items"], [])
        self.assertEqual(self.client.delete(f"/api/su-kien/{event_id}").status_code, 404)

        self.app.dependency_overrides[get_current_user] = lambda: self.user
        weekly = self.client.get("/api/su-kien/tuan", params={"bat_dau": date.today().isoformat()})
        self.assertEqual(weekly.status_code, 200, weekly.text)
        self.assertEqual(weekly.json()["tong_su_kien"], 1)
        combined = self.client.post("/api/tong-the", json={
            "ngay": 15, "thang": 6, "nam": 1995,
            "gioi_tinh": "nam", "huong_nha": "Nam",
            "ngay_bat_dau": date.today().isoformat(),
        })
        self.assertEqual(combined.status_code, 200, combined.text)
        self.assertIsNone(combined.json()["moi_truong"])
        self.assertEqual(combined.json()["su_kien"]["tong_su_kien"], 1)

    def test_feng_shui_input_validation_and_environment_key_requirement(self) -> None:
        invalid = self.client.post("/api/phong-thuy/phan-tich", json={
            "ngay": 31, "thang": 2, "nam": 1995, "huong_nha": "Tây Bắc",
        })
        self.assertEqual(invalid.status_code, 422)
        with patch.dict(os.environ, {}, clear=True):
            no_key = self.client.post("/api/moi-truong/hien-tai", json={"lat": 0, "lon": 0})
        self.assertEqual(no_key.status_code, 503)

    def test_geocode_is_persisted_per_user_and_reused_without_provider_call(self) -> None:
        from auth import get_current_user

        provider_response = httpx.Response(
            200,
            json={
                "features": [{
                    "properties": {
                        "lat": 10.234,
                        "lon": 106.367,
                        "formatted": "Bến Tre, Việt Nam",
                        "city": "Bến Tre",
                        "country": "Việt Nam",
                        "place_id": "place-1",
                    }
                }]
            },
            request=httpx.Request("GET", "https://api.geoapify.com/v1/geocode/search"),
        )
        with patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test-key"}):
            with patch("routes.geocode.httpx.AsyncClient") as client_class:
                provider = client_class.return_value.__aenter__.return_value
                provider.get = AsyncMock(return_value=provider_response)
                first = self.client.post(
                    "/api/geocode/", json={"address": " Nguyễn Văn Tư Bến Tre "}
                )
                second = self.client.post(
                    "/api/geocode/", json={"address": "nguyễn   văn tư bến tre"}
                )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["cached"])
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(second.json()["cached"])
        self.assertEqual(provider.get.await_count, 1)
        saved_location = self.client.get("/api/geocode/history").json()["items"][0]
        self.assertEqual(saved_location["lat"], 10.234)

        self.app.dependency_overrides[get_current_user] = lambda: self.other_user
        self.assertEqual(self.client.get("/api/geocode/history").json()["items"], [])
        self.assertEqual(
            self.client.delete(
                f"/api/geocode/history/{saved_location['id']}"
            ).status_code,
            404,
        )
        with patch.dict(os.environ, {}, clear=True):
            uncached = self.client.post(
                "/api/geocode/", json={"address": "Nguyễn Văn Tư Bến Tre"}
            )
        self.assertEqual(uncached.status_code, 503)
        self.assertEqual(provider.get.await_count, 1)

    def test_recent_weather_snapshot_is_reused_without_api_key_or_provider_call(self) -> None:
        environment = {
            "thoi_tiet": {
                "nhiet_do_c": 30.0,
                "do_am_phan_tram": 60,
                "mo_ta": "trời quang",
                "gio_m_s": 2.0,
                "thanh_pho": "Bến Tre",
            },
            "khong_khi": {"aqi": 2, "muc_do": "Khá", "pm2_5": 10, "pm10": 20},
            "nguon": "OpenWeather",
            "ghi_chu": "Tọa độ chỉ dùng để truy vấn.",
        }
        payload = {
            "ngay": 15,
            "thang": 6,
            "nam": 1995,
            "gioi_tinh": "nam",
            "huong_nha": "Nam",
            "lat": 10.234,
            "lon": 106.367,
        }
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test-key"}):
            with patch(
                "main.lay_du_lieu_moi_truong",
                new_callable=AsyncMock,
                return_value=environment,
            ) as provider:
                first = self.client.post("/api/tong-the", json=payload)
                with patch.dict(os.environ, {}, clear=True):
                    second = self.client.post("/api/tong-the", json=payload)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["moi_truong"]["lich_su"]["tai_su_dung"])
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(second.json()["moi_truong"]["lich_su"]["tai_su_dung"])
        self.assertEqual(provider.await_count, 1)
        saved = self.client.get("/api/geocode/history").json()["items"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["weather"]["nguon"], "OpenWeather")
        self.assertIsNotNone(saved[0]["weatherFetchedAt"])

        from database import LocationHistory, utcnow_naive

        with self.factory() as db:
            location = db.query(LocationHistory).one()
            location.weather_fetched_at = utcnow_naive() - timedelta(minutes=16)
            db.commit()
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test-key"}):
            with patch(
                "main.lay_du_lieu_moi_truong",
                new_callable=AsyncMock,
                return_value=environment,
            ) as refresh_provider:
                refreshed = self.client.post("/api/tong-the", json=payload)
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertFalse(refreshed.json()["moi_truong"]["lich_su"]["tai_su_dung"])
        refresh_provider.assert_awaited_once()

    def test_level_four_routes_validate_input_and_do_not_store_submitted_locations(self) -> None:
        from auth import get_current_user
        from database import Profile

        for page in (
            "/ban-do", "/gia-dao", "/kinh-te", "/trach-cat",
            "/tam-linh", "/video", "/so-sanh",
        ):
            self.assertEqual(self.client.get(page).status_code, 200, page)

        with self.factory() as db:
            profile_count_before = db.query(Profile).count()
        map_result = self.client.post("/api/ban-do/phan-tich", json={
            "lat": 21.0285, "lon": 105.8542, "huong_dat": "Bắc",
        })
        self.assertEqual(map_result.status_code, 200, map_result.text)
        self.assertEqual(map_result.json()["dia_hinh"]["do_cao_m"], None)
        self.assertEqual(map_result.json()["huong_dat_do_nguoi_dung_cung_cap"], "Bắc")
        with self.factory() as db:
            self.assertEqual(db.query(Profile).count(), profile_count_before)
        invalid_map = self.client.post("/api/ban-do/phan-tich", json={
            "lat": 91, "lon": 0, "huong_dat": "Bắc",
        })
        self.assertEqual(invalid_map.status_code, 422)
        with patch.dict(os.environ, {}, clear=True):
            elevation_without_key = self.client.post("/api/ban-do/phan-tich", json={
                "lat": 21.0285, "lon": 105.8542,
                "huong_dat": "Bắc", "truy_van_do_cao": True,
            })
        self.assertEqual(elevation_without_key.status_code, 503)

        family = self.client.post("/api/gia-dao/phan-tich", json={"thanh_vien": [
            {"ten": "Người 1", "vai_tro": "bố", "ngay_sinh": "1990-01-01", "gioi_tinh": "nam"},
        ]})
        self.assertEqual(family.status_code, 200, family.text)
        self.assertNotIn("1990-01-01", family.text)
        dates = self.client.post("/api/trach-cat/tim-ngay", json={
            "loai_viec": "gap_go",
            "tu_ngay": "2025-05-01",
            "so_ngay_tim": 3,
            "so_ket_qua": 2,
        })
        self.assertEqual(dates.status_code, 200, dates.text)
        self.assertEqual(len(dates.json()["top_ngay_tham_khao"]), 2)
        self.assertEqual(self.client.get("/api/tam-linh/thoi-khoa").status_code, 200)
        self.assertEqual(self.client.post("/api/tu-vi-tay/chart", json={
            "ngay": 31, "thang": 2, "nam": 1995,
        }).status_code, 422)

        self.app.dependency_overrides.pop(get_current_user)
        self.assertEqual(
            self.client.post("/api/ban-do/phan-tich", json={
                "lat": 0, "lon": 0, "huong_dat": "Bắc",
            }).status_code,
            401,
        )

    def test_market_route_surfaces_provider_failures(self) -> None:
        with patch("main.lay_du_lieu_thi_truong", new_callable=AsyncMock) as provider:
            provider.return_value = {"vn_index": {"gia_tri": 1}, "usd_vnd": {"usd_vnd": 2}}
            result = self.client.get("/api/kinh-te/thi-truong")
            self.assertEqual(result.status_code, 200, result.text)

            provider.side_effect = RuntimeError("provider unavailable")
            failed = self.client.get("/api/kinh-te/thi-truong")
            self.assertEqual(failed.status_code, 502)
            self.assertEqual(failed.json()["detail"], "provider unavailable")

    def test_birth_name_and_hour_are_saved_in_owned_profile(self) -> None:
        from main import BirthInput, _prepare_analysis
        from database import Profile

        with self.factory() as db:
            first = _prepare_analysis(
                BirthInput(
                    ho_ten="  Nguyễn Ái  ",
                    ngay=15,
                    thang=6,
                    nam=1995,
                    gio_sinh=0,
                ),
                self.user,
                db,
            )
            self.assertEqual(first[1]["ho_ten"], "Nguyễn Ái")
            self.assertEqual(first[1]["gio_sinh"], 0)
            self.assertEqual(first[1]["gio_sinh_phan_tich"]["can_chi_gio"].split()[1], "Tý")

            retained = _prepare_analysis(
                BirthInput(ngay=15, thang=6, nam=1995),
                self.user,
                db,
            )
            self.assertEqual(retained[1]["ho_ten"], "Nguyễn Ái")
            self.assertEqual(retained[1]["gio_sinh"], 0)
            saved = db.query(Profile).filter_by(user_id=self.user.id).one()
            self.assertIn('"gio_sinh": 0', saved.profile_json)

        invalid_hour = self.client.post("/api/analyze", json={
            "ngay": 15, "thang": 6, "nam": 1995, "gio_sinh": 24,
        })
        self.assertEqual(invalid_hour.status_code, 422)

    def test_i18n_endpoints_select_supported_languages(self) -> None:
        self.assertEqual(
            self.client.get("/api/i18n", headers={"Accept-Language": "ja,en;q=0.7"}).json()["lang"],
            "ja",
        )
        english = self.client.get("/api/i18n/en")
        self.assertEqual(english.status_code, 200)
        self.assertEqual(english.json()["translations"]["nav.home"], "🏠 Overview")
        self.assertEqual(self.client.get("/api/i18n/xx").status_code, 404)
        self.assertEqual(self.client.get("/i18n.js").status_code, 200)


if __name__ == "__main__":
    unittest.main()
