from pathlib import Path


def test_web_root_redirect_exists():
    middleware = Path(__file__).parents[2] / "web" / "middleware.ts"
    content = middleware.read_text(encoding="utf-8")
    assert "request.nextUrl.pathname === '/'" in content
    assert "new URL('/fa', request.url)" in content
    assert "matcher: ['/']" in content


def test_production_compose_runs_background_services_and_asset_volume():
    compose = (Path(__file__).parents[3] / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "worker:" in compose
    assert "scheduler:" in compose
    assert "ASSET_STORAGE_ROOT: /app/storage/assets" in compose
    assert "asset_data:/app/storage/assets" in compose
