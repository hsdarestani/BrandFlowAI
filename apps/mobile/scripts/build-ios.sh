#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ "$(uname -s)" != "Darwin" ]; then echo "iOS builds require the Publisher macOS agent." >&2; exit 2; fi
XCODE_VERSION="$(xcodebuild -version | awk '/Xcode/{print $2}' | head -n1)"; XCODE_MAJOR="${XCODE_VERSION%%.*}"
if [ -z "$XCODE_MAJOR" ] || [ "$XCODE_MAJOR" -lt 26 ]; then echo "App Store uploads require Xcode 26 or newer; found ${XCODE_VERSION:-unknown}." >&2; exit 3; fi
python3 scripts/store_positioning_check.py
if [ ! -d node_modules ]; then npm install; fi
if [ -d ios ] && [ ! -d ios/App ]; then rm -rf ios; fi
if [ ! -d ios/App ]; then npx cap add ios; fi
npx cap sync ios
npx @capacitor/assets generate --ios --iconBackgroundColor '#2563eb' --iconBackgroundColorDark '#2563eb' --splashBackgroundColor '#f5f7fb' --splashBackgroundColorDark '#f5f7fb' --logoSplashScale 0.34
PRIVACY_MANIFEST="$ROOT/ios/App/App/PrivacyInfo.xcprivacy"
cat > "$PRIVACY_MANIFEST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>NSPrivacyTracking</key><false/><key>NSPrivacyTrackingDomains</key><array/><key>NSPrivacyCollectedDataTypes</key><array/><key>NSPrivacyAccessedAPITypes</key><array/></dict></plist>
PLIST
mkdir -p artifacts build/ios
ARCHIVE="$ROOT/build/ios/Smarbiz.xcarchive"; EXPORT_DIR="$ROOT/build/ios/export"
VERSION="${APP_VERSION_NAME:-${APP_VERSION:-1.0.0}}"; BUILD="${APP_BUILD_NUMBER:-${BUILD_NUMBER:-1}}"
TEAM_ID="${APPLE_TEAM_ID:-${IOS_TEAM_ID:-}}"; AUTH_KEY_PATH="${APPLE_AUTH_KEY_PATH:-${APPLE_API_KEY_PATH:-}}"
SIGNING_STYLE="${IOS_SIGNING_STYLE:-Automatic}"; PROFILE_SPECIFIER="${IOS_PROVISIONING_PROFILE_SPECIFIER:-}"
CODE_SIGN_IDENTITY="${IOS_CODE_SIGN_IDENTITY:-Apple Distribution}"; SIGNING_KEYCHAIN="${IOS_SIGNING_KEYCHAIN:-}"
BUNDLE_ID="${IOS_BUNDLE_ID:-de.aplussolution.smarbiz}"
if [ -d ios/App/App.xcworkspace ]; then XCODE_CONTAINER=(-workspace ios/App/App.xcworkspace); elif [ -d ios/App/App.xcodeproj ]; then XCODE_CONTAINER=(-project ios/App/App.xcodeproj); else echo "No generated iOS Xcode project exists after cap sync." >&2; exit 6; fi
XCODE_ARGS=("${XCODE_CONTAINER[@]}" -scheme App -configuration Release -destination generic/platform=iOS -archivePath "$ARCHIVE" MARKETING_VERSION="$VERSION" CURRENT_PROJECT_VERSION="$BUILD" CODE_SIGN_STYLE="$SIGNING_STYLE" TARGETED_DEVICE_FAMILY=1 PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID" INFOPLIST_KEY_ITSAppUsesNonExemptEncryption=NO)
if [ -n "$TEAM_ID" ]; then XCODE_ARGS+=(DEVELOPMENT_TEAM="$TEAM_ID"); fi
if [ "$SIGNING_STYLE" = "Manual" ]; then
  if [ -z "$PROFILE_SPECIFIER" ] || [ -z "$SIGNING_KEYCHAIN" ]; then echo "Manual iOS signing requires Publisher provisioning profile and keychain." >&2; exit 7; fi
  XCODE_ARGS+=(CODE_SIGN_IDENTITY="$CODE_SIGN_IDENTITY" PROVISIONING_PROFILE_SPECIFIER="$PROFILE_SPECIFIER" "OTHER_CODE_SIGN_FLAGS=--keychain $SIGNING_KEYCHAIN")
elif [ -n "$AUTH_KEY_PATH" ] && [ -n "${APPLE_KEY_ID:-}" ] && [ -n "${APPLE_ISSUER_ID:-}" ]; then
  XCODE_ARGS+=(-allowProvisioningUpdates -authenticationKeyPath "$AUTH_KEY_PATH" -authenticationKeyID "$APPLE_KEY_ID" -authenticationKeyIssuerID "$APPLE_ISSUER_ID")
fi
xcodebuild "${XCODE_ARGS[@]}" clean archive
EXPORT_PLIST="$ROOT/build/ios/ExportOptions.plist"; TEAM_LINE=""; if [ -n "$TEAM_ID" ]; then TEAM_LINE="<key>teamID</key><string>${TEAM_ID}</string>"; fi
if [ "$SIGNING_STYLE" = "Manual" ]; then
cat > "$EXPORT_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>method</key><string>app-store-connect</string><key>signingStyle</key><string>manual</string><key>signingCertificate</key><string>${CODE_SIGN_IDENTITY}</string><key>provisioningProfiles</key><dict><key>${BUNDLE_ID}</key><string>${PROFILE_SPECIFIER}</string></dict><key>stripSwiftSymbols</key><true/><key>uploadSymbols</key><true/>${TEAM_LINE}</dict></plist>
PLIST
else
cat > "$EXPORT_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>method</key><string>app-store-connect</string><key>signingStyle</key><string>automatic</string><key>stripSwiftSymbols</key><true/><key>uploadSymbols</key><true/>${TEAM_LINE}</dict></plist>
PLIST
fi
rm -rf "$EXPORT_DIR"; EXPORT_ARGS=(-exportArchive -archivePath "$ARCHIVE" -exportPath "$EXPORT_DIR" -exportOptionsPlist "$EXPORT_PLIST")
if [ -n "$AUTH_KEY_PATH" ] && [ -n "${APPLE_KEY_ID:-}" ] && [ -n "${APPLE_ISSUER_ID:-}" ]; then EXPORT_ARGS+=(-allowProvisioningUpdates -authenticationKeyPath "$AUTH_KEY_PATH" -authenticationKeyID "$APPLE_KEY_ID" -authenticationKeyIssuerID "$APPLE_ISSUER_ID"); fi
xcodebuild "${EXPORT_ARGS[@]}"
IPA="$(find "$EXPORT_DIR" -name '*.ipa' -type f | head -n 1)"; if [ -z "$IPA" ]; then echo "No IPA was produced." >&2; exit 8; fi
cp "$IPA" artifacts/smarbiz.ipa
echo "iOS artifact: $ROOT/artifacts/smarbiz.ipa"
