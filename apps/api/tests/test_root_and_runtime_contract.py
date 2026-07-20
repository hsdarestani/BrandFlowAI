from pathlib import Path


def test_web_root_redirect_exists():
    root_page = Path(__file__).parents[2] / "web" / "app" / "page.tsx"
    content = root_page.read_text(encoding="utf-8")
    assert "redirect('/fa')" in content or 'redirect("/fa")' in content


def test_production_compose_runs_background_services_and_asset_volume():
    compose = (Path(__file__).parents[3] / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "worker:" in compose
    assert "scheduler:" in compose
    assert "ASSET_STORAGE_ROOT: /app/storage/assets" in compose
    assert "asset_data:/app/storage/assets" in compose
