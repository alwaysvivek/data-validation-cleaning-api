"""Shared test fixtures."""

import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture()
def messy_df():
    """A deliberately messy DataFrame for testing."""
    return pd.DataFrame({
        "First Name": ["  Alice  ", "Bob", "Charlie", "Alice", None, "  "],
        "Last Name": ["Smith", "Jones", "Brown", "Smith", "Williams", None],
        "Age": [30, None, 25, 30, 40, None],
        "Email": ["alice@test.com", "bob@test", "charlie@test.com", "alice@test.com", None, None],
        "Join Date": ["2023-01-15", "2023/02/20", "March 3, 2023", "2023-01-15", "2023-04-10", None],
    })


@pytest.fixture()
def clean_df():
    """A clean DataFrame with no issues."""
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [30, 25, 40],
        "email": ["alice@test.com", "bob@test.com", "charlie@test.com"],
    })


@pytest.fixture()
def messy_csv_bytes(messy_df):
    """Messy data serialized to CSV bytes."""
    buf = io.BytesIO()
    messy_df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture()
def messy_excel_bytes(messy_df):
    """Messy data serialized to Excel bytes."""
    buf = io.BytesIO()
    messy_df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()
