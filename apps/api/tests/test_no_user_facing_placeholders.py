from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOTS = [
    REPO_ROOT / "apps" / "web" / "app",
    REPO_ROOT / "apps" / "web" / "components",
]

# These phrases indicate fake/unfinished behavior when they appear in a
# user-facing component. Normal HTML placeholder= attributes are intentionally
# not banned.
FORBIDDEN = {
    "pdf coming soon",
    "coming soon",
    "delivered_mock",
    "mock_published",
    "not implemented yet",
    "fake success",
}


def test_no_obvious_placeholder_copy_in_user_facing_web_components():
    violations = []
    for root in WEB_ROOTS:
        for path in root.rglob("*.tsx"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for phrase in FORBIDDEN:
                if phrase in text:
                    violations.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")
    assert not violations, "User-facing placeholder copy found:\n" + "\n".join(violations)
