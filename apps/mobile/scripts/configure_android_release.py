#!/usr/bin/env python3
import os
import re
from pathlib import Path

build_gradle = Path("android/app/build.gradle")
variables = Path("android/variables.gradle")
if not build_gradle.exists():
    raise SystemExit("android/app/build.gradle not found; run npx cap add android first")

version_name = (os.environ.get("APP_VERSION_NAME") or os.environ.get("APP_VERSION") or "1.0.0").strip()
build_raw = (os.environ.get("APP_BUILD_NUMBER") or os.environ.get("BUILD_NUMBER") or "1").strip()
try:
    build_number = int(build_raw)
except ValueError as exc:
    raise SystemExit(f"APP_BUILD_NUMBER must be an integer, got: {build_raw}") from exc
if build_number < 1:
    raise SystemExit("APP_BUILD_NUMBER must be >= 1")

text = build_gradle.read_text(encoding="utf-8")
text, code_count = re.subn(r"(?m)^(\s*)versionCode\s+\d+\s*$", rf"\1versionCode {build_number}", text, count=1)
text, name_count = re.subn(r"(?m)^(\s*)versionName\s+[\"\'][^\"\']*[\"\']\s*$", rf'\1versionName "{version_name}"', text, count=1)
if code_count != 1 or name_count != 1:
    raise SystemExit("Could not locate generated Android versionCode/versionName")
build_gradle.write_text(text, encoding="utf-8")

if not variables.exists():
    raise SystemExit("android/variables.gradle not found")
v = variables.read_text(encoding="utf-8")
v, compile_count = re.subn(r"(?m)^(\s*)compileSdkVersion\s*=\s*\d+\s*$", r"\1compileSdkVersion = 36", v, count=1)
v, target_count = re.subn(r"(?m)^(\s*)targetSdkVersion\s*=\s*\d+\s*$", r"\1targetSdkVersion = 36", v, count=1)
if compile_count != 1 or target_count != 1:
    raise SystemExit("Could not enforce Android compile/target SDK 36")
variables.write_text(v, encoding="utf-8")
print(f"Configured Android versionName={version_name}, versionCode={build_number}, targetSdk=36")
