from collections import defaultdict

from app.entrypoint import app


def test_every_http_path_method_has_one_handler():
    """Prevent a legacy placeholder route from shadowing a production override."""
    seen = defaultdict(list)
    for route in app.router.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        for method in (getattr(route, "methods", set()) or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            seen[(path, method)].append(getattr(route, "name", "<unnamed>"))

    duplicates = {
        f"{method} {path}": names
        for (path, method), names in seen.items()
        if len(names) > 1
    }
    assert not duplicates, "Duplicate API handlers can shadow production routes: " + repr(duplicates)
