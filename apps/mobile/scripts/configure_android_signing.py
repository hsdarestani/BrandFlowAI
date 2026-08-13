#!/usr/bin/env python3
from pathlib import Path

path = Path("android/app/build.gradle")
if not path.exists():
    raise SystemExit("android/app/build.gradle not found; run npx cap add android first")
text = path.read_text(encoding="utf-8")
marker = "// SMARBIZ_PUBLISHER_SIGNING"
if marker in text:
    print("Android signing already configured.")
    raise SystemExit(0)
signing = r'''
    // SMARBIZ_PUBLISHER_SIGNING
    signingConfigs {
        smarbizRelease {
            storeFile file(System.getenv("SMARBIZ_KEYSTORE_FILE"))
            storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyAlias System.getenv("ANDROID_KEY_ALIAS")
            keyPassword System.getenv("ANDROID_KEY_PASSWORD")
        }
    }
'''
if "    buildTypes {" not in text:
    raise SystemExit("Could not locate buildTypes in generated Gradle file")
text = text.replace("    buildTypes {", signing + "\n    buildTypes {", 1)
needle = "        release {"
if needle not in text:
    raise SystemExit("Could not locate release build type")
text = text.replace(needle, needle + "\n            signingConfig signingConfigs.smarbizRelease", 1)
path.write_text(text, encoding="utf-8")
print("Configured Android release signing from Publisher environment.")
