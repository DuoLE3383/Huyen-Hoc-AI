"""HTML-to-PDF export with escaped templates and bounded document size."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
MAX_HTML_BYTES = 500_000
MAX_PDF_BYTES = 20_000_000
_environment = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)


def render_pdf(html_content: str) -> bytes:
    if len(html_content.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("Nội dung PDF vượt quá giới hạn cho phép.")
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "PDF cần WeasyPrint và các thư viện đồ họa hệ thống của nền tảng."
        ) from exc
    try:
        pdf = HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf()
    except OSError as exc:
        raise RuntimeError(
            "Không thể khởi tạo thư viện đồ họa cần thiết để tạo PDF."
        ) from exc
    if len(pdf) > MAX_PDF_BYTES:
        raise ValueError("Tệp PDF vượt quá giới hạn dung lượng.")
    return pdf


def _render(template_name: str, **context: Any) -> bytes:
    template = _environment.get_template(template_name)
    html = template.render(
        **context,
        brand="Huyền Học AI",
        ngay_xuat=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    return render_pdf(html)


def export_la_so_pdf(
    la_so: dict[str, Any],
    luan_giai: dict[str, Any] | None = None,
    user_name: str = "Người dùng",
) -> bytes:
    return _render(
        "la_so.html",
        la_so=la_so,
        luan_giai=luan_giai,
        user_name=user_name[:100],
    )


def export_ban_menh_pdf(
    profile: dict[str, Any],
    chi_so: dict[str, Any],
    phan_tich: dict[str, Any],
    user_name: str = "Người dùng",
) -> bytes:
    return _render(
        "ban_menh.html",
        profile=profile,
        chi_so=chi_so,
        phan_tich=phan_tich,
        user_name=user_name[:100],
    )
