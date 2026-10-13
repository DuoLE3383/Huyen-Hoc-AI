#!/usr/bin/env python3
"""Patch CSS cho frontend/phong-thuy.html — chạy 1 lần, tự backup."""
import re
import shutil
from pathlib import Path

HTML = Path("/mnt/d/Documents/GitHub/Huyen Hoc AI/frontend/phong-thuy.html")
BACKUP = HTML.with_suffix(".html.bak-before-css")

# 1. Backup
if not BACKUP.exists():
    shutil.copy(HTML, BACKUP)
    print(f"✅ Backup: {BACKUP}")

content = HTML.read_text(encoding="utf-8")

# 2. Thay block CSS cũ bằng block mới
OLD_CSS_MARKERS = [
    # .row > label
    (r"\.row>label \{[^}]*\}", """\
.row>label {
      flex: 1 1 180px;
      min-width: 0
    }

    .row>label input,
    .row>label select {
      width: 100%
    }"""),
    # pre
    (r"    pre \{[^}]*\}", """\
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      max-height: 500px;
      overflow-y: auto;
      padding: 12px;
      background: #0f0519;
      border-radius: 8px;
      border: 1px solid #2f1d47
    }"""),
    # address-input
    (r"\.address-input \{[^}]*\}", """\
.address-input {
      display: flex;
      gap: 8px;
      align-items: stretch
    }"""),
    # address-input input
    (r"\.address-input input \{[^}]*\}", """\
.address-input input,
    .address-input select {
      flex: 1;
      min-width: 0
    }"""),
    # geocode-result
    (r"\.geocode-result \{[^}]*\}", """\
.geocode-result {
      margin: 12px 0;
      padding: 12px 14px;
      border-left: 3px solid #10b981;
      border-radius: 6px;
      background: #10b98115;
      font-size: 14px;
      line-height: 1.6
    }"""),
    # btn-secondary
    (r"\.btn-secondary \{[^}]*\}", """\
.btn-secondary {
      background: #4c2f8f;
      border: 1px solid #705d83;
      white-space: nowrap;
      flex-shrink: 0;
      min-height: 42px
    }"""),
]

changed = 0
for pattern, replacement in OLD_CSS_MARKERS:
    new_content, n = re.subn(pattern, replacement, content, count=1)
    if n > 0:
        content = new_content
        changed += 1
        print(f"✅ Patched: {pattern[:40]}...")
    else:
        print(f"⚠️  Not found: {pattern[:40]}...")

HTML.write_text(content, encoding="utf-8")
print(f"\n✅ Done. {changed}/{len(OLD_CSS_MARKERS)} blocks patched.")
print(f"   Backup: {BACKUP}")
