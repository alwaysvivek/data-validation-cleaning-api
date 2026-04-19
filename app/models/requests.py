"""Pydantic request models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CleaningOptions(BaseModel):
    """Configurable cleaning behaviour sent by the client."""

    remove_duplicates: bool = True
    handle_nulls: Literal[
        "drop", "fill_mean", "fill_median", "fill_mode", "fill_empty"
    ] = "drop"
    strip_whitespace: bool = True
    standardize_columns: bool = True
    remove_empty_rows: bool = True
    convert_dates: bool = True


class DataPayload(BaseModel):
    """JSON-based data input."""

    data: list[dict] = Field(..., min_length=1, description="List of row dictionaries")
    options: CleaningOptions = Field(default_factory=CleaningOptions)


class StandardizeRequest(BaseModel):
    """Request body for AI standardization."""

    values: list[str] = Field(..., min_length=1, description="Messy values to standardize")
    context: str = Field("", description="Optional context, e.g. 'US state names'")


class AIRequest(BaseModel):
    """Unified request body for AI analysis."""

    action: Literal["suggest", "profile", "standardize"]
    data: list[dict] = Field(default_factory=list, description="Dataset rows (for suggest/profile)")
    values: list[str] = Field(default_factory=list, description="Messy values (for standardize)")
    context: str = Field("", description="Optional context (for standardize)")
