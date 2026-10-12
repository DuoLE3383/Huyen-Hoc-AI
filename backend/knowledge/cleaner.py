"""
Clean text — fix lỗi OCR phổ biến của tuvi.cohoc.net.
"""
import re
import unicodedata
from pathlib import Path
from typing import Dict


# Bảng fix lỗi OCR
OCR_FIXES = {
    # Ký tự Cyrillic lẫn trong tiếng Việt
    "\u0441": "c",  # с (Cyrillic) → c
    "\u0430": "a",  # а → a
    "\u0435": "e",  # е → e
    "\u043e": "o",  # о → o
    "\u0440": "p",  # р → p
    "\u0445": "x",  # х → x
    "\u0443": "y",  # у → y
    "\u0456": "i",  # і → i

    # Từ lỗi phổ biến
    "lăng hay giảm": "làm tăng hay giảm",
    "mác nạn": "mắc nạn",
    "mác bệnh": "mắc bệnh",
    "mác kiện": "mắc kiện",
    "mác tù tội": "mắc tù tội",
    "sổng nước": "sông nước",
    "phòng lửa": "phỏng lửa",
    "thông manh": "thong manh",
    "chóc lở": "chốc lở",
    "ma qủy": "ma quỷ",
    "Nga đau": "Ngã đau",
    "mộng tình": "mộng tinh",
    "sẩn thận": "cẩn thận",
    "thủ thủ cung": "tọa thủ cung",
    "hư hại": "hư hại",
    "tì vết": "tỳ vết",
    "nhức đầu": "nhức đầu",
    "mụn nhọt": "mụn nhọt",
    "đậu sởi": "đậu sởi",
    "mộc dục": "Mộc Dục",
    "phạm phòng": "phạm phòng",
    "áo dà": "ào ạt",
    "tầu": "tàu",
    "tâu": "tâu",
    "1. Ảnh hưởng": "## 1. Ảnh hưởng",
    "2. Ảnh hưởng": "## 2. Ảnh hưởng",
    "3. Ảnh hưởng": "## 3. Ảnh hưởng",
}


class TextCleaner:
    def __init__(self):
        self.fixes = OCR_FIXES

    def normalize_unicode(self, text: str) -> str:
        """Chuẩn hóa Unicode NFC cho tiếng Việt"""
        return unicodedata.normalize("NFC", text)

    def fix_cyrillic(self, text: str) -> str:
        """Fix ký tự Cyrillic lẫn trong text"""
        cyrillic_chars = "\u0400-\u04FF"
        # Đầu tiên map các ký tự phổ biến
        for cyr, lat in self.fixes.items():
            if len(cyr) == 1:
                text = text.replace(cyr, lat)
        return text

    def fix_common_errors(self, text: str) -> str:
        """Fix các lỗi OCR phổ biến"""
        for wrong, right in self.fixes.items():
            if len(wrong) > 1:  # Chỉ apply cho từ/cụm từ
                text = text.replace(wrong, right)
        return text

    def fix_headings(self, text: str) -> str:
        """Chuẩn hóa headings markdown"""
        # Number headings
        text = re.sub(r"^(\d+\.\d+\.)\s+", r"### \1 ", text, flags=re.MULTILINE)
        text = re.sub(r"^(\d+\.)\s+", r"## \1 ", text, flags=re.MULTILINE)
        return text

    def fix_whitespace(self, text: str) -> str:
        """Chuẩn hóa whitespace"""
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def clean(self, text: str) -> str:
        """Pipeline clean đầy đủ"""
        text = self.normalize_unicode(text)
        text = self.fix_cyrillic(text)
        text = self.fix_common_errors(text)
        text = self.fix_headings(text)
        text = self.fix_whitespace(text)
        return text

    def clean_file(self, filepath: Path) -> bool:
        """Clean 1 file markdown"""
        content = filepath.read_text(encoding="utf-8")

        # Tách frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                cleaned_body = self.clean(body)
                new_content = f"---{frontmatter}---\n{cleaned_body}"
                filepath.write_text(new_content, encoding="utf-8")
                return True

        # Không có frontmatter
        cleaned = self.clean(content)
        filepath.write_text(cleaned, encoding="utf-8")
        return True


# === SỬ DỤNG ===
if __name__ == "__main__":
    cleaner = TextCleaner()
    kb_dir = Path(__file__).parent.parent / "data" / "knowledge_base" / "tu_vi"

    md_files = list(kb_dir.glob("*.md"))
    print(f"🧹 Cleaning {len(md_files)} files...")

    for md_file in md_files:
        cleaner.clean_file(md_file)
        print(f"   ✅ {md_file.name}")

    print(f"\n✅ Đã clean {len(md_files)} files")