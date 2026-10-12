"""Small, static translation catalog for the web application's shared labels."""

from typing import Any

from fastapi import Request

LANG_DEFAULT = "vi"
LANG_SUPPORTED = ("vi", "en", "zh", "ja")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "vi": {
        "app.title": "🔮 Huyền Học AI",
        "app.subtitle": "Phân tích bản mệnh · Gợi ý tham khảo · Ghi nhận phản hồi",
        "nav.label": "Điều hướng",
        "nav.home": "🏠 Tổng quan",
        "nav.tuvi": "🀄 Tử Vi",
        "nav.dashboard": "📈 Dashboard",
        "nav.compatibility": "🤝 Hợp tuổi & chia sẻ",
        "nav.tarot": "🃏 Tarot",
        "nav.iching": "☯ Kinh Dịch",
        "nav.fengshui": "🏠 Phong thủy",
        "nav.events": "📅 Sự kiện",
        "nav.timeline": "🌏 Timeline",
        "nav.map": "🗺️ Bản đồ",
        "nav.family": "👨‍👩‍👧 Gia đạo",
        "nav.economy": "📊 Kinh tế",
        "nav.almanac": "🏯 Trạch cát",
        "nav.mindfulness": "🕉️ Tâm linh",
        "nav.video": "🎥 Video",
        "nav.comparison": "🔮 Đông–Tây",
        "nav.logout": "🚪 Đăng xuất",
        "profile.heading": "Thông tin ngày sinh",
        "profile.saved": "Hồ sơ đã lưu",
        "profile.saved.placeholder": "Chọn hồ sơ đã lưu…",
        "profile.name": "Họ tên (không bắt buộc)",
        "profile.day": "Ngày",
        "profile.month": "Tháng",
        "profile.year": "Năm",
        "profile.birth_hour": "Giờ sinh địa phương (không bắt buộc, 0–23)",
        "profile.analyze": "✨ Phân tích bản mệnh",
        "profile.export": "📄 Xuất bản mệnh PDF",
        "profile.ab": "🧪 Phân tích trong thử nghiệm A/B",
        "language.label": "Ngôn ngữ",
        "i18n.error": "Không tải được bản dịch; giao diện giữ nguyên ngôn ngữ hiện tại.",
    },
    "en": {
        "app.title": "🔮 Huyen Hoc AI",
        "app.subtitle": "Birth profile · Cultural reference · Feedback",
        "nav.label": "Navigation",
        "nav.home": "🏠 Overview",
        "nav.tuvi": "🀄 Zi Wei",
        "nav.dashboard": "📈 Dashboard",
        "nav.compatibility": "🤝 Compatibility & sharing",
        "nav.tarot": "🃏 Tarot",
        "nav.iching": "☯ I Ching",
        "nav.fengshui": "🏠 Feng shui",
        "nav.events": "📅 Events",
        "nav.timeline": "🌏 Timeline",
        "nav.map": "🗺️ Map",
        "nav.family": "👨‍👩‍👧 Family",
        "nav.economy": "📊 Economy",
        "nav.almanac": "🏯 Almanac",
        "nav.mindfulness": "🕉️ Mindfulness",
        "nav.video": "🎥 Video",
        "nav.comparison": "🔮 East–West",
        "nav.logout": "🚪 Log out",
        "profile.heading": "Birth details",
        "profile.saved": "Saved profiles",
        "profile.saved.placeholder": "Choose a saved profile…",
        "profile.name": "Full name (optional)",
        "profile.day": "Day",
        "profile.month": "Month",
        "profile.year": "Year",
        "profile.birth_hour": "Local birth hour (optional, 0–23)",
        "profile.analyze": "✨ Analyze profile",
        "profile.export": "📄 Export profile PDF",
        "profile.ab": "🧪 Run A/B analysis",
        "language.label": "Language",
        "i18n.error": "Could not load translations; the current language is unchanged.",
    },
    "zh": {
        "app.title": "🔮 玄学 AI",
        "app.subtitle": "出生资料 · 文化参考 · 用户反馈",
        "nav.label": "导航",
        "nav.home": "🏠 概览",
        "nav.tuvi": "🀄 紫微斗数",
        "nav.dashboard": "📈 仪表板",
        "nav.compatibility": "🤝 合盘与分享",
        "nav.tarot": "🃏 塔罗",
        "nav.iching": "☯ 易经",
        "nav.fengshui": "🏠 风水",
        "nav.events": "📅 事件",
        "nav.timeline": "🌏 时间线",
        "nav.map": "🗺️ 地图",
        "nav.family": "👨‍👩‍👧 家庭",
        "nav.economy": "📊 经济",
        "nav.almanac": "🏯 黄历参考",
        "nav.mindfulness": "🕉️ 正念",
        "nav.video": "🎥 视频",
        "nav.comparison": "🔮 东西方",
        "nav.logout": "🚪 退出",
        "profile.heading": "出生信息",
        "profile.saved": "已保存资料",
        "profile.saved.placeholder": "选择已保存的资料…",
        "profile.name": "姓名（可选）",
        "profile.day": "日",
        "profile.month": "月",
        "profile.year": "年",
        "profile.birth_hour": "当地出生时间（可选，0–23）",
        "profile.analyze": "✨ 分析资料",
        "profile.export": "📄 导出资料 PDF",
        "profile.ab": "🧪 运行 A/B 分析",
        "language.label": "语言",
        "i18n.error": "无法加载翻译；当前语言保持不变。",
    },
    "ja": {
        "app.title": "🔮 Huyen Hoc AI",
        "app.subtitle": "出生プロフィール · 文化的な参考 · フィードバック",
        "nav.label": "ナビゲーション",
        "nav.home": "🏠 概要",
        "nav.tuvi": "🀄 紫微斗数",
        "nav.dashboard": "📈 ダッシュボード",
        "nav.compatibility": "🤝 相性と共有",
        "nav.tarot": "🃏 タロット",
        "nav.iching": "☯ 易経",
        "nav.fengshui": "🏠 風水",
        "nav.events": "📅 イベント",
        "nav.timeline": "🌏 タイムライン",
        "nav.map": "🗺️ 地図",
        "nav.family": "👨‍👩‍👧 家族",
        "nav.economy": "📊 経済",
        "nav.almanac": "🏯 暦の参考",
        "nav.mindfulness": "🕉️ マインドフルネス",
        "nav.video": "🎥 動画",
        "nav.comparison": "🔮 東洋・西洋",
        "nav.logout": "🚪 ログアウト",
        "profile.heading": "出生情報",
        "profile.saved": "保存済みプロフィール",
        "profile.saved.placeholder": "保存済みプロフィールを選択…",
        "profile.name": "氏名（任意）",
        "profile.day": "日",
        "profile.month": "月",
        "profile.year": "年",
        "profile.birth_hour": "現地出生時刻（任意、0–23）",
        "profile.analyze": "✨ プロフィールを分析",
        "profile.export": "📄 プロフィール PDF を出力",
        "profile.ab": "🧪 A/B 分析を実行",
        "language.label": "言語",
        "i18n.error": "翻訳を読み込めません。現在の言語を維持します。",
    },
}


def detect_lang(request: Request) -> str:
    query_lang = request.query_params.get("lang", "").lower()
    if query_lang in LANG_SUPPORTED:
        return query_lang

    accepted = []
    for item in request.headers.get("accept-language", "").split(","):
        parts = item.strip().split(";")
        language = parts[0].strip().split("-", 1)[0].lower()
        if language in LANG_SUPPORTED:
            try:
                quality = float(parts[1].strip().removeprefix("q=")) if len(parts) > 1 else 1.0
            except ValueError:
                quality = 0.0
            accepted.append((quality, language))
    return max(accepted, default=(0.0, LANG_DEFAULT))[1]


def t(key: str, lang: str = LANG_DEFAULT, **kwargs: Any) -> str:
    value = TRANSLATIONS.get(lang, TRANSLATIONS[LANG_DEFAULT]).get(
        key, TRANSLATIONS[LANG_DEFAULT].get(key, key)
    )
    try:
        return value.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return value
