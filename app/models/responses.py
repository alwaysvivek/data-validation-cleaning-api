"""Pydantic response models."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data Quality Score
# ---------------------------------------------------------------------------
class DataQualityScore(BaseModel):
    """Composite quality score based on null %, duplicates, and type consistency."""

    overall: float = Field(..., ge=0, le=100, description="Weighted overall score 0-100")
    null_score: float = Field(..., ge=0, le=100)
    duplicate_score: float = Field(..., ge=0, le=100)
    consistency_score: float = Field(..., ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class ValidationReport(BaseModel):
    """Report produced by the validation step."""

    total_rows: int
    total_columns: int
    null_counts: dict[str, int]
    duplicate_row_count: int
    column_types: dict[str, str]
    issues: list[str]
    quality_score: DataQualityScore


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
class CleaningReport(BaseModel):
    """Summary of what the cleaning step changed."""

    rows_before: int
    rows_after: int
    duplicates_removed: int
    nulls_handled: int
    columns_renamed: dict[str, str]


# ---------------------------------------------------------------------------
# Process (main pipeline result)
# ---------------------------------------------------------------------------
class ProcessResult(BaseModel):
    """Full pipeline output returned by /process endpoints."""

    validation: ValidationReport
    cleaning: CleaningReport
    quality_score_before: DataQualityScore
    quality_score_after: DataQualityScore
    data: list[dict[str, Any]]
    processing_time_ms: float
    ai_summary: Optional[str] = None
    ai_profile: Optional[str] = None


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
class PreviewResult(BaseModel):
    """Lightweight preview of an uploaded dataset."""

    rows: list[dict[str, Any]]
    column_names: list[str]
    column_types: dict[str, str]
    total_rows: int
    quality_score: DataQualityScore


# ---------------------------------------------------------------------------
# AI responses
# ---------------------------------------------------------------------------
class AISuggestion(BaseModel):
    """A single AI-generated cleaning suggestion."""

    column: str
    issue: str
    suggestion: str
    confidence: float = Field(..., ge=0, le=1)


class AIStandardizeResult(BaseModel):
    """Result of LLM-based value standardization."""

    original_values: list[str]
    standardized_values: list[str]
    mapping: dict[str, str]


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Schema for structured error responses (used in OpenAPI docs)."""

    error: str
    message: str
    detail: dict[str, Any] = {}
    timestamp: str
