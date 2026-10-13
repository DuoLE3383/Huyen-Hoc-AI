#!/usr/bin/env python3
"""Chèn <link app.css> vào tất cả HTML trong frontend/ (idempotent)."""
import pathlib, sys, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
LINK = '  <link rel="stylesheet" href="/static/css/app.css">\n'
MARKER = "static/css/app.css"

files = sorted(FRONTEND.glob("*.html")) + sorted(FRONTEND.glob("pages/*.html"))
changed, skipped, failed = 0, 0, 0

for f in files:
    try:
        html = f.read_text(encoding="utf-8")
    except Exception as e:
        print(f"✗ {f.relative_to(ROOT)}: {e}")
        failed += 1
        continue

    if MARKER in html:
        print(f"· skip {f.relative_to(ROOT)}")
        skipped += 1
        continue

    if "</head>" not in html:
        print(f"✗ {f.relative_to(ROOT)}: no </head>")
        failed += 1
        continue

    # Chèn ngay trước </head>, sau </title> hoặc <meta> cuối cùng
    new_html = html.replace("</head>", LINK + "</head>", 1)
    f.write_text(new_html, encoding="utf-8")
    print(f"✓ {f.relative_to(ROOT)}")
    changed += 1

print(f"\n📊 changed={changed}  skipped={skipped}  failed={failed}  total={len(files)}")
sys.exit(1 if failed else 0)
