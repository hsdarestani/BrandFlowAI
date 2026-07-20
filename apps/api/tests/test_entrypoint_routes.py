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
