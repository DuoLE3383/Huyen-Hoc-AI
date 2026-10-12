"""Gentle optional mindfulness practices, not spiritual or medical diagnosis."""

PRACTICES = {
    "breathing": {
        "ten": "Thở chậm, tự nhiên",
        "thoi_luong_phut": 3,
        "cac_buoc": [
            "Ngồi hoặc đứng ở tư thế thoải mái.",
            "Thở tự nhiên, thả lỏng vai; không nín thở hoặc cố hít thật sâu.",
            "Nếu thấy chóng mặt hay khó chịu, dừng lại và trở về nhịp thở bình thường.",
        ],
    },
    "grounding": {
        "ten": "Định hướng giác quan",
        "thoi_luong_phut": 3,
        "cac_buoc": [
            "Nhẹ nhàng nhận biết ba điều bạn nhìn thấy.",
            "Nhận biết hai âm thanh và một cảm giác cơ thể dễ chịu.",
            "Không cần thay đổi cảm giác; có thể dừng bất cứ lúc nào.",
        ],
    },
    "gratitude": {
        "ten": "Ghi nhận điều tích cực",
        "thoi_luong_phut": 5,
        "cac_buoc": [
            "Viết một điều nhỏ bạn muốn ghi nhận hôm nay.",
            "Viết một việc thực tế, vừa sức mà bạn có thể làm tiếp theo.",
        ],
    },
}


def tao_thoi_khoa_tam_linh() -> dict[str, object]:
    return {
        "thuc_hanh_tu_chon": list(PRACTICES.values()),
        "goi_y": ["Chọn một bài ngắn, bỏ qua nếu không phù hợp."],
        "ghi_chu": (
            "Thiền, mantra và chakra được trình bày như thực hành/văn hóa tự nguyện, "
            "không chẩn đoán sức khỏe hay trạng thái tâm lý và không thay thế chăm sóc chuyên môn."
        ),
    }
