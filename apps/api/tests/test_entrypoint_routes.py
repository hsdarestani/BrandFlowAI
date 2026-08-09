from app.entrypoint import app


def _matching_routes(path: str, method: str):
    return [
        route
        for route in app.router.routes
        if getattr(route, "path", None) == path
        and method.upper() in (getattr(route, "methods", set()) or set())
    ]


def test_asset_download_uses_single_file_streaming_route():
    routes = _matching_routes("/assets/{id}/download", "GET")
    assert len(routes) == 1
    assert routes[0].name == "asset_download_file"


def test_report_email_uses_single_brevo_route():
    routes = _matching_routes("/reports/{id}/send-email", "POST")
    assert len(routes) == 1
    assert routes[0].name == "report_send_email_brevo"


def test_calendar_week_generation_uses_single_brand_aware_route():
    routes = _matching_routes("/calendar/generate-week", "POST")
    assert len(routes) == 1
    assert routes[0].name == "calendar_generate_week_brand_aware"


def test_brand_calendar_generation_routes_are_non_duplicate():
    generate = _matching_routes("/brands/{id}/calendar/generate-week", "POST")
    regenerate = _matching_routes("/brands/{id}/calendar/regenerate-week", "POST")
    assert len(generate) == 1
    assert len(regenerate) == 1
    assert generate[0].name == "brand_calendar_generate_week_brand_aware"
    assert regenerate[0].name == "brand_calendar_regenerate_week_brand_aware"
