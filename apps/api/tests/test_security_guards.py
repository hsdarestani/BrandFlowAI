from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def signup(prefix: str):
    suffix = uuid4().hex
    response = client.post(
        "/auth/signup",
        json={
            "email": f"{prefix}-{suffix}@example.com",
            "password": "password123",
            "name": prefix,
            "organization_name": f"{prefix} {suffix}",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_public_signup_cannot_create_superadmin():
    suffix = uuid4().hex
    response = client.post(
        "/auth/signup",
        json={
            "email": f"admin-{suffix}@example.com",
            "password": "password123",
            "name": "Public Admin Attempt",
            "organization_name": "Public Admin Attempt",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_super_admin"] is False


def test_organization_and_brand_ids_are_tenant_scoped():
    first = signup("tenant-a")
    second = signup("tenant-b")
    first_headers = auth(first["access_token"])

    assert client.get(f"/organizations/{second['organization']['id']}", headers=first_headers).status_code == 403
    assert client.patch(
        f"/organizations/{second['organization']['id']}",
        headers=first_headers,
        json={"name": "Cross-tenant change"},
    ).status_code == 403
    assert client.get(f"/brands/{second['brand']['id']}", headers=first_headers).status_code == 403
    assert client.delete(f"/brands/{second['brand']['id']}", headers=first_headers).status_code == 403


def test_brand_creation_cannot_target_another_organization():
    first = signup("creator-a")
    second = signup("creator-b")
    response = client.post(
        "/brands",
        headers=auth(first["access_token"]),
        json={
            "organization_id": second["organization"]["id"],
            "name": "Foreign brand",
            "industry": "general",
            "country": "DE",
            "primary_language": "en",
            "timezone": "Europe/Berlin",
            "description": "Should be rejected",
        },
    )
    assert response.status_code == 403


def test_protected_organization_fields_require_superadmin():
    account = signup("protected-field")
    response = client.patch(
        f"/organizations/{account['organization']['id']}",
        headers=auth(account["access_token"]),
        json={"owner_user_id": 999999},
    )
    assert response.status_code == 403
