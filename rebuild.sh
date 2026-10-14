#!/usr/bin/env bash
# rebuild.sh — Auto version (semver) + đổi tên app + build APK
set -e
cd "$(dirname "$0")"

APP_NAME="Kinh Dịch AI"

# ─── Version dạng 1.YYYY.MMDD+HHMM ───
YEAR=$(date +%Y)
DDMM=$(date +%d%m)
HHMM=$(date +%H%M)
VERSION="2.${DDMM}.${YEAR}.${HHMM}"
echo "📱 Version: $VERSION"

# ─── 1. Đổi tên app ───
sed -i "s|<string name=\"app_name\">.*</string>|<string name=\"app_name\">$APP_NAME</string>|" \
  android/app/src/main/res/values/strings.xml
sed -i "s|<string name=\"title_activity_main\">.*</string>|<string name=\"title_activity_main\">$APP_NAME</string>|" \
  android/app/src/main/res/values/strings.xml

.venv/bin/python -c "
import json, pathlib
p = pathlib.Path('capacitor.config.json')
cfg = json.loads(p.read_text())
cfg['appName'] = '$APP_NAME'
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
"
echo "✅ App: $APP_NAME"

# ─── 2. Ghi version vào build.gradle ───
if [ -f "android/app/build.gradle" ]; then
  # versionCode giữ cố định = 1 (tránh overflow 2^31)
  # versionName update mỗi build
  sed -i "s|versionName \"[^\"]*\"|versionName \"$VERSION\"|" android/app/build.gradle
  echo "✅ Android versionName=$VERSION (versionCode giữ nguyên)"
fi

# ─── 3. Cache buster HTML ───
sed -i "s|bundle.js?v=[^\"']*|bundle.js?v=$VERSION|g" frontend/pages/kinh-dich.html
sed -i "s|kinh-dich.css?v=[^\"']*|kinh-dich.css?v=$VERSION|g" frontend/pages/kinh-dich.html
sed -i "s|app.css?v=[^\"']*|app.css?v=$VERSION|g" frontend/pages/kinh-dich.html
echo "✅ HTML cache buster → $VERSION"

# ─── 4. Inject version vào HTML footer ───
.venv/bin/python <<PYEOF
import pathlib, re
p = pathlib.Path("frontend/pages/kinh-dich.html")
s = p.read_text(encoding="utf-8")
# Xoá version cũ nếu có
s = re.sub(r'<p class="kd-version">.*?</p>', '', s)
# Thêm version mới trước </main>
s = s.replace("</main>", f'  <p class="kd-version">v$VERSION</p>\n    </main>', 1)
p.write_text(s, encoding="utf-8")
print("✅ Footer version → v$VERSION")
PYEOF

# ─── 5. Sync ───
echo
echo "🔄 Sync Capacitor..."
npx cap sync 2>&1 | tail -3

# ─── 6. Build APK ───
echo
echo "🔨 Build APK..."
cd android
./gradlew assembleDebug 2>&1 | tail -3

APK="app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK" ]; then
  SIZE=$(stat -c%s "$APK" | numfmt --to=iec 2>/dev/null || stat -c%s "$APK")
  TIMESTAMP=$(stat -c '%y' "$APK" | cut -d. -f1)
  echo
  echo "═══════════════════════════════════════════"
  echo "✅ APK: $APK ($SIZE)"
  echo "⏰ Build: $TIMESTAMP"
  echo "📱 Version: $VERSION"
  echo "📝 App: $APP_NAME"
  echo "═══════════════════════════════════════════"
else
  echo "❌ Build failed"
  exit 1
fi