#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "🔄 Sync Capacitor..."
npx cap sync 2>&1 | tail -3
echo "🔨 Build APK..."
cd android
./gradlew assembleDebug 2>&1 | tail -3
APK="app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK" ]; then
  SIZE=$(stat -c%s "$APK" | numfmt --to=iec)
  echo "✅ APK: $(pwd)/$APK ($SIZE)"
else
  echo "❌ Build failed"
  exit 1
fi
