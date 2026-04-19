"""Tests for the /preview/file endpoint."""

import io


def test_preview_returns_rows(client, messy_csv_bytes):
    resp = client.post(
        "/api/v1/preview/file",
        files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "rows" in body
    assert len(body["rows"]) <= 10


def test_preview_returns_column_info(client, messy_csv_bytes):
    resp = client.post(
        "/api/v1/preview/file",
        files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
    )
    body = resp.json()
    assert "column_names" in body
    assert "column_types" in body
    assert len(body["column_names"]) > 0


def test_preview_returns_quality_score(client, messy_csv_bytes):
    resp = client.post(
        "/api/v1/preview/file",
        files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
    )
    body = resp.json()
    score = body["quality_score"]
    assert 0 <= score["overall"] <= 100
    assert score["grade"] in ("A", "B", "C", "D", "F")


def test_preview_works_with_excel(client, messy_excel_bytes):
    resp = client.post(
        "/api/v1/preview/file",
        files={"file": ("test.xlsx", io.BytesIO(messy_excel_bytes), "application/octet-stream")},
    )
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) > 0


def test_preview_total_rows(client, messy_csv_bytes):
    resp = client.post(
        "/api/v1/preview/file",
        files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
    )
    body = resp.json()
    assert body["total_rows"] >= len(body["rows"])
