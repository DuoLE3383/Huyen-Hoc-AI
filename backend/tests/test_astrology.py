import unittest

from services.astrology import (
    phan_tich_gio_sinh,
    phan_tich_ngay_sinh,
    phan_tich_ten,
    tinh_can_chi_nam,
    tinh_chi_so_su_kien,
    tinh_menh_ngu_hanh,
    tinh_so_chu_dao,
)


class AstrologyTests(unittest.TestCase):
    def test_can_chi_and_nap_am_cycle(self) -> None:
        self.assertEqual(tinh_can_chi_nam(1984), "Giáp Tý")
        self.assertEqual(tinh_menh_ngu_hanh(1984), "Kim")
        self.assertEqual(tinh_menh_ngu_hanh(1985), "Kim")
        self.assertEqual(tinh_menh_ngu_hanh(1986), "Hỏa")

    def test_life_path_reduces_to_single_digit(self) -> None:
        self.assertEqual(tinh_so_chu_dao(15, 6, 1995), 9)

    def test_profile_and_event_scores_are_complete_and_bounded(self) -> None:
        profile = phan_tich_ngay_sinh(15, 6, 1995)
        scores = tinh_chi_so_su_kien(profile)
        self.assertEqual(profile["ngay_sinh"], "15/06/1995")
        self.assertEqual(
            set(scores),
            {"tai_van", "tinh_duyen", "su_nghiep", "suc_khoe", "gap_go", "thay_doi"},
        )
        self.assertTrue(all(0 <= score <= 100 for score in scores.values()))

    def test_vietnamese_name_numbers_normalize_diacritics_and_disclaim_claims(self) -> None:
        accented = phan_tich_ten("Nguyễn Ái")
        unaccented = phan_tich_ten("Nguyen Ai")
        self.assertEqual(accented["so_linh_hon"], unaccented["so_linh_hon"])
        self.assertEqual(accented["so_nhan_cach"], unaccented["so_nhan_cach"])
        self.assertIn("không phải phép đo", accented["ghi_chu"])
        self.assertIsNone(phan_tich_ten("山田")["so_su_menh"])

    def test_birth_hour_boundaries_and_optional_profile_fields(self) -> None:
        at_midnight = phan_tich_gio_sinh(15, 6, 1995, 0)
        at_eleven = phan_tich_gio_sinh(15, 6, 1995, 23)
        self.assertEqual(at_midnight["can_chi_gio"].split()[1], "Tý")
        self.assertEqual(at_eleven["can_chi_gio"].split()[1], "Tý")
        self.assertIn("múi giờ", at_midnight["ghi_chu"])
        with self.assertRaises(ValueError):
            phan_tich_gio_sinh(15, 6, 1995, 24)

        profile = phan_tich_ngay_sinh(15, 6, 1995, "Nguyễn Ái", 0)
        self.assertEqual(profile["ho_ten"], "Nguyễn Ái")
        self.assertEqual(profile["gio_sinh"], 0)
        self.assertIn("ten_phan_tich", profile)
        self.assertIn("gio_sinh_phan_tich", profile)


if __name__ == "__main__":
    unittest.main()
