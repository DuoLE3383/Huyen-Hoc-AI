"""Lập lá số tham khảo; phần an sao là mô hình giản lược, không thay thế chuyên gia."""

import math
from datetime import date
from typing import Any

CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]
CUNG = [
    "Mệnh", "Phụ Mẫu", "Phúc Đức", "Điền Trạch", "Quan Lộc", "Nô Bộc",
    "Thiên Di", "Tật Ách", "Tài Bạch", "Tử Tức", "Phu Thê", "Huynh Đệ",
]
NAP_AM = [
    "Kim", "Hỏa", "Mộc", "Thổ", "Kim", "Hỏa", "Thủy", "Thổ", "Kim", "Mộc",
    "Thủy", "Thổ", "Hỏa", "Mộc", "Thủy", "Kim", "Hỏa", "Mộc", "Thổ", "Kim",
    "Hỏa", "Thủy", "Thổ", "Kim", "Mộc", "Thủy", "Thổ", "Hỏa", "Mộc", "Thủy",
]
CUC_BY_ELEMENT = {
    "Thủy": "Thủy Nhị Cục",
    "Mộc": "Mộc Tam Cục",
    "Kim": "Kim Tứ Cục",
    "Thổ": "Thổ Ngũ Cục",
    "Hỏa": "Hỏa Lục Cục",
}
CUC_NUMBER = {"Thủy Nhị Cục": 2, "Mộc Tam Cục": 3, "Kim Tứ Cục": 4, "Thổ Ngũ Cục": 5, "Hỏa Lục Cục": 6}
CHINH_TINH = [
    "Tử Vi", "Thiên Cơ", "Thái Dương", "Vũ Khúc", "Thiên Đồng", "Liêm Trinh",
    "Thiên Phủ", "Thái Âm", "Tham Lang", "Cự Môn", "Thiên Tướng", "Thiên Lương",
    "Thất Sát", "Phá Quân",
]
TRANG_THAI = {
    "Tử Vi": ["Bình", "Vượng", "Miếu", "Vượng", "Đắc", "Miếu", "Miếu", "Vượng", "Đắc", "Vượng", "Miếu", "Vượng"],
    "Thiên Cơ": ["Miếu", "Đắc", "Đắc", "Vượng", "Miếu", "Hãm", "Hãm", "Đắc", "Vượng", "Miếu", "Hãm", "Hãm"],
    "Thái Dương": ["Hãm", "Hãm", "Vượng", "Miếu", "Miếu", "Vượng", "Đắc", "Đắc", "Bình", "Hãm", "Hãm", "Bình"],
    "Vũ Khúc": ["Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Bình", "Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Bình"],
    "Thiên Đồng": ["Vượng", "Đắc", "Hãm", "Hãm", "Bình", "Vượng", "Miếu", "Đắc", "Hãm", "Hãm", "Bình", "Vượng"],
    "Liêm Trinh": ["Miếu", "Bình", "Vượng", "Hãm", "Hãm", "Vượng", "Miếu", "Bình", "Vượng", "Hãm", "Hãm", "Vượng"],
    "Thiên Phủ": ["Miếu", "Vượng", "Đắc", "Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Đắc"],
    "Thái Âm": ["Miếu", "Vượng", "Đắc", "Bình", "Hãm", "Hãm", "Bình", "Đắc", "Vượng", "Miếu", "Vượng", "Đắc"],
    "Tham Lang": ["Bình", "Hãm", "Miếu", "Vượng", "Đắc", "Bình", "Hãm", "Miếu", "Vượng", "Đắc", "Bình", "Hãm"],
    "Cự Môn": ["Vượng", "Miếu", "Đắc", "Vượng", "Bình", "Hãm", "Hãm", "Bình", "Vượng", "Miếu", "Đắc", "Vượng"],
    "Thiên Tướng": ["Miếu", "Đắc", "Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Đắc", "Vượng", "Miếu", "Đắc", "Vượng"],
    "Thiên Lương": ["Miếu", "Vượng", "Đắc", "Miếu", "Vượng", "Đắc", "Miếu", "Vượng", "Đắc", "Miếu", "Vượng", "Đắc"],
    "Thất Sát": ["Miếu", "Vượng", "Đắc", "Bình", "Hãm", "Vượng", "Miếu", "Vượng", "Đắc", "Bình", "Hãm", "Vượng"],
    "Phá Quân": ["Miếu", "Vượng", "Đắc", "Hãm", "Bình", "Vượng", "Miếu", "Vượng", "Đắc", "Hãm", "Bình", "Vượng"],
}


class AmLich:
    """Chuyển đổi dương lịch/âm lịch theo lịch Việt Nam (UTC+7)."""

    @staticmethod
    def jd_from_date(day: date) -> int:
        a = (14 - day.month) // 12
        year = day.year + 4800 - a
        month = day.month + 12 * a - 3
        return (
            day.day + (153 * month + 2) // 5 + 365 * year + year // 4
            - year // 100 + year // 400 - 32045
        )

    @staticmethod
    def new_moon_day(k: int, time_zone: float = 7.0) -> int:
        t = k / 1236.85
        t2, t3 = t * t, t * t * t
        radians = math.pi / 180
        jd = 2415020.75933 + 29.53058868 * k + 0.0001178 * t2 - 0.000000155 * t3
        jd += 0.00033 * math.sin((166.56 + 132.87 * t - 0.009173 * t2) * radians)
        mean_sun = 359.2242 + 29.10535608 * k - 0.0000333 * t2 - 0.00000347 * t3
        mean_moon = 306.0253 + 385.81691806 * k + 0.0107306 * t2 + 0.00001236 * t3
        moon_argument = 21.2964 + 390.67050646 * k - 0.0016528 * t2 - 0.00000239 * t3
        correction = (0.1734 - 0.000393 * t) * math.sin(mean_sun * radians)
        correction += 0.0021 * math.sin(2 * mean_sun * radians)
        correction -= 0.4068 * math.sin(mean_moon * radians)
        correction += 0.0161 * math.sin(2 * mean_moon * radians)
        correction -= 0.0004 * math.sin(3 * mean_moon * radians)
        correction += 0.0104 * math.sin(2 * moon_argument * radians)
        correction -= 0.0051 * math.sin((mean_sun + mean_moon) * radians)
        correction -= 0.0074 * math.sin((mean_sun - mean_moon) * radians)
        correction += 0.0004 * math.sin((2 * moon_argument + mean_sun) * radians)
        correction -= 0.0004 * math.sin((2 * moon_argument - mean_sun) * radians)
        correction -= 0.0006 * math.sin((2 * moon_argument + mean_moon) * radians)
        correction += 0.0010 * math.sin((2 * moon_argument - mean_moon) * radians)
        correction += 0.0005 * math.sin((2 * mean_moon + mean_sun) * radians)
        if t < -11:
            delta_t = 0.001 + 0.000839 * t + 0.0002261 * t2 - 0.00000845 * t3 - 0.000000081 * t * t3
        else:
            delta_t = -0.000278 + 0.000265 * t + 0.000262 * t2
        return math.floor(jd + correction - delta_t + 0.5 + time_zone / 24)

    @staticmethod
    def sun_longitude_sector(day_number: int, time_zone: float = 7.0) -> int:
        t = (day_number - 2451545.5 - time_zone / 24) / 36525
        t2 = t * t
        radians = math.pi / 180
        mean_anomaly = 357.52910 + 35999.05030 * t - 0.0001559 * t2 - 0.00000048 * t2 * t
        mean_longitude = 280.46645 + 36000.76983 * t + 0.0003032 * t2
        delta = (1.914600 - 0.004817 * t - 0.000014 * t2) * math.sin(mean_anomaly * radians)
        delta += (0.019993 - 0.000101 * t) * math.sin(2 * mean_anomaly * radians)
        delta += 0.000290 * math.sin(3 * mean_anomaly * radians)
        longitude = (mean_longitude + delta) % 360
        return math.floor(longitude / 30)

    @classmethod
    def lunar_month_11(cls, year: int, time_zone: float = 7.0) -> int:
        offset = cls.jd_from_date(date(year, 12, 31)) - 2415021
        k = math.floor(offset / 29.530588853)
        new_moon = cls.new_moon_day(k, time_zone)
        if cls.sun_longitude_sector(new_moon, time_zone) >= 9:
            new_moon = cls.new_moon_day(k - 1, time_zone)
        return new_moon

    @classmethod
    def leap_month_offset(cls, month_11: int, time_zone: float = 7.0) -> int:
        k = math.floor(0.5 + (month_11 - 2415021.076998695) / 29.530588853)
        last_arc = -1
        index = 1
        arc = cls.sun_longitude_sector(cls.new_moon_day(k + index, time_zone), time_zone)
        while arc != last_arc and index < 14:
            last_arc = arc
            index += 1
            arc = cls.sun_longitude_sector(cls.new_moon_day(k + index, time_zone), time_zone)
        return index - 1

    @classmethod
    def solar_to_lunar(
        cls, day: date, time_zone: float = 7.0
    ) -> tuple[int, int, int, bool]:
        jd = cls.jd_from_date(day)
        k = math.floor((jd - 2415021.076998695) / 29.530588853)
        month_start = cls.new_moon_day(k + 1, time_zone)
        if month_start > jd:
            month_start = cls.new_moon_day(k, time_zone)

        month_11 = cls.lunar_month_11(day.year, time_zone)
        next_month_11 = month_11
        if month_11 >= month_start:
            lunar_year = day.year
            month_11 = cls.lunar_month_11(day.year - 1, time_zone)
        else:
            lunar_year = day.year + 1
            next_month_11 = cls.lunar_month_11(day.year + 1, time_zone)

        lunar_day = jd - month_start + 1
        month_difference = math.floor((month_start - month_11) / 29.0)
        lunar_month = month_difference + 11
        is_leap_month = False
        if next_month_11 - month_11 > 365:
            leap_offset = cls.leap_month_offset(month_11, time_zone)
            if month_difference >= leap_offset:
                lunar_month = month_difference + 10
                is_leap_month = month_difference == leap_offset
        if lunar_month > 12:
            lunar_month -= 12
        if lunar_month >= 11 and month_difference < 4:
            lunar_year -= 1
        return lunar_day, lunar_month, lunar_year, is_leap_month


def _nap_am(stem_index: int, branch_index: int) -> str:
    for cycle_index in range(60):
        if cycle_index % 10 == stem_index and cycle_index % 12 == branch_index:
            return NAP_AM[cycle_index // 2]
    raise ValueError("Can Chi không hợp lệ.")


def cuc_menh(menh_branch_index: int, year_stem_index: int) -> str:
    # Ngũ Hổ Độn: tìm Can cung Dần rồi suy ra Can tại cung Mệnh.
    stem_at_dan = (year_stem_index % 5 * 2 + 2) % 10
    palace_stem = (stem_at_dan + menh_branch_index - 2) % 10
    palace_element = _nap_am(palace_stem, menh_branch_index)
    return CUC_BY_ELEMENT[palace_element]


def an_tu_vi(cuc: str, lunar_day: int) -> int:
    bureau_number = CUC_NUMBER[cuc]
    quotient = math.ceil(lunar_day / bureau_number)
    remainder = quotient * bureau_number - lunar_day
    position = quotient + (remainder if remainder % 2 == 0 else -remainder)
    return (2 + position - 1) % 12


def an_14_chinh_tinh(tu_vi_index: int) -> dict[str, int]:
    positions = {
        "Tử Vi": tu_vi_index,
        "Thiên Cơ": (tu_vi_index - 1) % 12,
        "Thái Dương": (tu_vi_index - 3) % 12,
        "Vũ Khúc": (tu_vi_index - 4) % 12,
        "Thiên Đồng": (tu_vi_index - 5) % 12,
        "Liêm Trinh": (tu_vi_index - 8) % 12,
    }
    tian_fu = (4 - tu_vi_index) % 12
    positions.update({
        "Thiên Phủ": tian_fu,
        "Thái Âm": (tian_fu + 1) % 12,
        "Tham Lang": (tian_fu + 2) % 12,
        "Cự Môn": (tian_fu + 3) % 12,
        "Thiên Tướng": (tian_fu + 4) % 12,
        "Thiên Lương": (tian_fu + 5) % 12,
        "Thất Sát": (tian_fu + 6) % 12,
        "Phá Quân": (tian_fu + 10) % 12,
    })
    return positions


def an_phu_tinh(
    year_stem_index: int, year_branch_index: int, hour_index: int, lunar_month: int
) -> dict[str, list[int]]:
    khôi = {0: 1, 1: 0, 2: 11, 3: 11, 4: 1, 5: 0, 6: 1, 7: 7, 8: 6, 9: 3}
    việt = {0: 7, 1: 8, 2: 4, 3: 5, 4: 7, 5: 8, 6: 7, 7: 1, 8: 2, 9: 5}
    lộc = {0: 2, 1: 3, 2: 5, 3: 6, 4: 5, 5: 6, 6: 8, 7: 9, 8: 11, 9: 0}
    đào = {0: 9, 1: 6, 2: 3, 3: 0, 4: 9, 5: 6, 6: 3, 7: 0, 8: 9, 9: 6, 10: 3, 11: 0}
    hồng = {0: 3, 1: 2, 2: 1, 3: 0, 4: 11, 5: 10, 6: 9, 7: 8, 8: 7, 9: 6, 10: 5, 11: 4}
    loc_index = lộc[year_stem_index]
    return {
        "Tả Phù": [(2 + lunar_month - 1) % 12],
        "Hữu Bật": [(10 - (lunar_month - 1)) % 12],
        "Văn Xương": [(10 - hour_index) % 12],
        "Văn Khúc": [(4 + hour_index) % 12],
        "Thiên Khôi": [khôi[year_stem_index]],
        "Thiên Việt": [việt[year_stem_index]],
        "Lộc Tồn": [loc_index],
        "Kình Dương": [(loc_index + 1) % 12],
        "Đà La": [(loc_index - 1) % 12],
        "Hỏa Tinh": [(2 + hour_index) % 12],
        "Linh Tinh": [(10 - hour_index) % 12],
        "Đào Hoa": [đào[year_branch_index]],
        "Hồng Loan": [hồng[year_branch_index]],
    }


def lap_la_so(day: int, month: int, year: int, hour: int = 0) -> dict[str, Any]:
    birth_date = date(year, month, day)
    if not 0 <= hour <= 23:
        raise ValueError("Giờ sinh phải nằm trong khoảng 0–23.")
    lunar_day, lunar_month, lunar_year, is_leap = AmLich.solar_to_lunar(birth_date)
    year_stem_index = (lunar_year - 4) % 10
    year_branch_index = (lunar_year - 4) % 12
    hour_index = ((hour + 1) // 2) % 12
    life_branch_index = (2 + lunar_month - 1 - hour_index) % 12
    body_branch_index = (2 + lunar_month - 1 + hour_index) % 12
    bureau = cuc_menh(life_branch_index, year_stem_index)
    ziwei_index = an_tu_vi(bureau, lunar_day)
    main_positions = an_14_chinh_tinh(ziwei_index)
    auxiliary_positions = an_phu_tinh(
        year_stem_index, year_branch_index, hour_index, lunar_month
    )

    palaces = []
    for palace_offset, palace_name in enumerate(CUNG):
        branch_index = (life_branch_index - palace_offset) % 12
        main_stars = [
            {"sao": star, "trang_thai": TRANG_THAI[star][branch_index]}
            for star, position in main_positions.items()
            if position == branch_index
        ]
        auxiliary_stars = [
            star for star, positions in auxiliary_positions.items()
            if branch_index in positions
        ]
        palaces.append({
            "cung": palace_name,
            "dia_chi": CHI[branch_index],
            "vi_tri": branch_index,
            "la_menh": branch_index == life_branch_index,
            "la_than": branch_index == body_branch_index,
            "chinh_tinh": main_stars,
            "phu_tinh": auxiliary_stars,
        })

    lunar_label = f"{lunar_day:02d}/{lunar_month:02d}/{lunar_year}"
    if is_leap:
        lunar_label += " (nhuận)"
    return {
        "duong_lich": birth_date.strftime("%d/%m/%Y"),
        "am_lich": lunar_label,
        "can_chi_nam": f"{CAN[year_stem_index]} {CHI[year_branch_index]}",
        "gio_sinh": f"{hour:02d}:00 (Canh {CHI[hour_index]})",
        "cuc": bureau,
        "menh_chi": CHI[life_branch_index],
        "than_chi": CHI[body_branch_index],
        "tu_vi_tai": CHI[ziwei_index],
        "cung": palaces,
        "ghi_chu": (
            "Ngày âm lịch tính theo UTC+7. Cách an sao, cục và trạng thái sao ở đây "
            "được giản lược để tham khảo, có thể khác trường phái Tử Vi."
        ),
    }
