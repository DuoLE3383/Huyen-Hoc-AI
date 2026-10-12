import unittest

from astrology import (
    phan_tich_ngay_sinh,
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


if __name__ == "__main__":
    unittest.main()
