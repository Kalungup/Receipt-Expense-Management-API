from fastapi.testclient import TestClient

import pytest

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):

    database = tmp_path / "test.db"

    monkeypatch.setenv(
        "DATABASE_PATH",
        str(database)
    )

    with TestClient(app) as test_client:
        yield test_client


def sample_receipt():

    return {
        "merchant": "ICA",
        "amount": "249.90",
        "currency": "SEK",
        "category": "Groceries",
        "purchase_date": "2026-11-09"
    }


def test_health(client):

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "healthy"


def test_create_receipt(client):

    response = client.post(
        "/receipts",
        json=sample_receipt()
    )

    assert response.status_code == 201

    data = response.json()

    assert data["merchant"] == "ICA"
    assert data["currency"] == "SEK"
    assert data["amount"] == "249.90"


def test_get_receipt(client):

    created = client.post(
        "/receipts",
        json=sample_receipt()
    )

    receipt_id = created.json()["id"]

    response = client.get(
        f"/receipts/{receipt_id}"
    )

    assert response.status_code == 200

    assert response.json()["merchant"] == "ICA"


def test_missing_receipt(client):

    response = client.get("/receipts/9999")

    assert response.status_code == 404


def test_invalid_amount(client):

    receipt = sample_receipt()
    receipt["amount"] = "-100"

    response = client.post(
        "/receipts",
        json=receipt
    )

    assert response.status_code == 422


def test_delete_receipt(client):

    created = client.post(
        "/receipts",
        json=sample_receipt()
    )

    receipt_id = created.json()["id"]

    deleted = client.delete(
        f"/receipts/{receipt_id}"
    )

    assert deleted.status_code == 204

    missing = client.get(
        f"/receipts/{receipt_id}"
    )

    assert missing.status_code == 404


def test_expense_summary(client):

    client.post(
        "/receipts",
        json=sample_receipt()
    )

    response = client.get("/receipts/summary")

    assert response.status_code == 200

    assert response.json()["total_receipts"] == 1