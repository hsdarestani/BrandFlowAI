#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 scripts/store_positioning_check.py
if [ ! -d node_modules ]; then npm install; fi
if [ -d android ] && [ ! -f android/gradlew ]; then rm -rf android; fi
if [ ! -f android/gradlew ]; then npx cap add android; fi
npx cap sync android
python3 scripts/configure_android_release.py
npx @capacitor/assets generate --android --iconBackgroundColor '#2563eb' --iconBackgroundColorDark '#2563eb' --splashBackgroundColor '#f5f7fb' --splashBackgroundColorDark '#f5f7fb' --logoSplashScale 0.34
mkdir -p artifacts
SIGNING_READY=0
if [ -n "${ANDROID_KEYSTORE_PATH:-}" ] && [ -f "${ANDROID_KEYSTORE_PATH}" ] && [ -n "${ANDROID_KEYSTORE_PASSWORD:-}" ] && [ -n "${ANDROID_KEY_ALIAS:-}" ] && [ -n "${ANDROID_KEY_PASSWORD:-}" ]; then
  export SMARBIZ_KEYSTORE_FILE="$ANDROID_KEYSTORE_PATH"; SIGNING_READY=1
elif [ -n "${ANDROID_KEYSTORE_BASE64:-}" ] && [ -n "${ANDROID_KEYSTORE_PASSWORD:-}" ] && [ -n "${ANDROID_KEY_ALIAS:-}" ] && [ -n "${ANDROID_KEY_PASSWORD:-}" ]; then
  printf '%s' "$ANDROID_KEYSTORE_BASE64" | base64 --decode > android/app/smarbiz-release.jks
  export SMARBIZ_KEYSTORE_FILE="$ROOT/android/app/smarbiz-release.jks"; SIGNING_READY=1
fi
if [ "$SIGNING_READY" = "1" ]; then
  python3 scripts/configure_android_signing.py
elif [ "${REQUIRE_ANDROID_SIGNING:-0}" = "1" ]; then
  echo "Android signing credentials are required but missing." >&2; exit 3
else
  echo "Signing credentials not supplied; building an unsigned verification bundle."
fi
(
  cd android
  for attempt in 1 2 3; do
    if ./gradlew --no-daemon clean bundleRelease; then exit 0; fi
    if [ "$attempt" -ge 3 ]; then echo "Gradle release build failed after $attempt attempts." >&2; exit 1; fi
    sleep $((attempt * 8))
  done
)
AAB="$(find android/app/build/outputs/bundle/release -name '*.aab' -type f | head -n 1)"
if [ -z "$AAB" ]; then echo "No release AAB was produced." >&2; exit 5; fi
cp "$AAB" artifacts/smarbiz-release.aab
echo "Android artifact: $ROOT/artifacts/smarbiz-release.aab"
