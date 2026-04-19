"""Tests for the /process endpoints."""

import io
import json


# ---------------------------------------------------------------------------
# JSON input
# ---------------------------------------------------------------------------
class TestProcessJSON:
    """Tests for POST /api/v1/process with JSON input."""

    def test_basic_process(self, client):
        payload = {
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": None},
                {"name": "Alice", "age": 30},
            ]
        }
        resp = client.post("/api/v1/process", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "validation" in body
        assert "cleaning" in body
        assert "quality_score_before" in body
        assert "quality_score_after" in body
        assert "data" in body
        assert "processing_time_ms" in body

    def test_quality_score_improves_after_cleaning(self, client):
        payload = {
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": None},
                {"name": "Alice", "age": 30},
                {"name": None, "age": None},
            ]
        }
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        assert body["quality_score_after"]["overall"] >= body["quality_score_before"]["overall"]

    def test_quality_score_has_grade(self, client):
        payload = {"data": [{"x": 1}, {"x": 2}]}
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        assert body["quality_score_after"]["grade"] in ("A", "B", "C", "D", "F")

    def test_duplicates_removed(self, client):
        payload = {
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]
        }
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        assert body["cleaning"]["duplicates_removed"] >= 1
        assert len(body["data"]) == 2

    def test_nulls_dropped(self, client):
        payload = {
            "data": [
                {"name": "Alice", "age": 30},
                {"name": None, "age": None},
            ],
            "options": {"handle_nulls": "drop"},
        }
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        assert body["cleaning"]["nulls_handled"] > 0
        assert len(body["data"]) == 1

    def test_nulls_filled_empty(self, client):
        payload = {
            "data": [
                {"name": "Alice", "age": 30},
                {"name": None, "age": None},
            ],
            "options": {"handle_nulls": "fill_empty", "remove_duplicates": False},
        }
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        assert len(body["data"]) == 2  # no rows dropped

    def test_column_standardization(self, client):
        payload = {
            "data": [{"First Name": "Alice", "Last Name": "Smith"}],
            "options": {"standardize_columns": True},
        }
        resp = client.post("/api/v1/process", json=payload)
        body = resp.json()
        keys = set(body["data"][0].keys())
        assert "first_name" in keys
        assert "last_name" in keys

    def test_limit_rows(self, client):
        payload = {
            "data": [{"x": i} for i in range(100)],
            "options": {"remove_duplicates": False},
        }
        resp = client.post("/api/v1/process?limit=10", json=payload)
        body = resp.json()
        assert len(body["data"]) <= 10

    def test_csv_export(self, client):
        payload = {"data": [{"name": "Alice"}, {"name": "Bob"}]}
        resp = client.post("/api/v1/process?format=csv", json=payload)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert b"name" in resp.content

    def test_excel_export(self, client):
        payload = {"data": [{"name": "Alice"}, {"name": "Bob"}]}
        resp = client.post("/api/v1/process?format=excel", json=payload)
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_empty_data_rejected(self, client):
        resp = client.post("/api/v1/process", json={"data": []})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# File input
# ---------------------------------------------------------------------------
class TestProcessFile:
    """Tests for POST /api/v1/process/file with file uploads."""

    def test_csv_upload(self, client, messy_csv_bytes):
        resp = client.post(
            "/api/v1/process/file",
            files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "quality_score_before" in body
        assert "quality_score_after" in body

    def test_excel_upload(self, client, messy_excel_bytes):
        resp = client.post(
            "/api/v1/process/file",
            files={"file": ("test.xlsx", io.BytesIO(messy_excel_bytes), "application/octet-stream")},
        )
        assert resp.status_code == 200

    def test_unsupported_file_type(self, client):
        resp = client.post(
            "/api/v1/process/file",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 422
        assert resp.json()["error"] == "UNSUPPORTED_FILE_TYPE"

    def test_csv_export_from_file(self, client, messy_csv_bytes):
        resp = client.post(
            "/api/v1/process/file?format=csv",
            files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_custom_options_via_form(self, client, messy_csv_bytes):
        opts = json.dumps({"handle_nulls": "fill_empty", "remove_duplicates": False})
        resp = client.post(
            "/api/v1/process/file",
            files={"file": ("test.csv", io.BytesIO(messy_csv_bytes), "text/csv")},
            data={"options": opts},
        )
        assert resp.status_code == 200
        body = resp.json()
        # With fill_empty + no dedup, should retain more rows
        assert body["cleaning"]["rows_after"] >= 3


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------
class TestErrorResponses:
    """Verify structured error format."""

    def test_error_has_structure(self, client):
        resp = client.post(
            "/api/v1/process/file",
            files={"file": ("bad.txt", io.BytesIO(b"data"), "text/plain")},
        )
        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert "timestamp" in body

    def test_processing_time_header(self, client):
        payload = {"data": [{"x": 1}]}
        resp = client.post("/api/v1/process", json=payload)
        assert "x-processing-time-ms" in resp.headers
