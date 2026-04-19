"""Core processing routes — preview, process (JSON + file), export."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, Query, UploadFile, Request, Header
from fastapi.responses import StreamingResponse

from app.limiter import limiter

from app.config import settings
from app.errors import ProcessingError
from app.models.requests import CleaningOptions, DataPayload
from app.models.responses import PreviewResult, ProcessResult
from app.services.cleaner import DataCleaner
from app.services.file_handler import FileHandler
from app.services.validator import DataValidator
from app.services.ai_service import GroqAIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Process"])

# Instantiate services
validator = DataValidator()
cleaner = DataCleaner()
file_handler = FileHandler()

def _merge_dfs(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Intelligently merge multiple DataFrames based on common keys or orientation."""
    if not dfs:
        return pd.DataFrame()
    if len(dfs) == 1:
        return dfs[0]
        
    merged = dfs[0]
    for next_df in dfs[1:]:
        common = list(set(merged.columns) & set(next_df.columns))
        if common:
            # Join on common columns (IDs, Categories, etc.)
            merged = pd.merge(merged, next_df, on=common, how="outer")
        else:
            # No common columns? Side-by-side concatenation
            merged = pd.concat([merged, next_df], axis=1)
    return merged

# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
@router.post("/preview/file", response_model=PreviewResult)
@limiter.limit("20/minute")
async def preview_file(request: Request, files: list[UploadFile] = File(...)):
    """Upload multiple files and get a quick preview of the merged result."""
    dfs = []
    for file in files:
        df = await file_handler.read_upload(file)
        dfs.append(df)
        
    df = _merge_dfs(dfs)
    n = settings.DEFAULT_PREVIEW_ROWS
    
    # Offload CPU-bound task to thread
    quality = await asyncio.to_thread(validator.compute_quality_score, df)
    
    column_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # Convert preview rows, handling NaN → None for JSON serialization
    preview_df = df.head(n)
    rows = json.loads(preview_df.to_json(orient="records", date_format="iso"))

    return PreviewResult(
        rows=rows,
        column_names=list(df.columns),
        column_types=column_types,
        total_rows=len(df),
        quality_score=quality,
    )


# ---------------------------------------------------------------------------
# Process — JSON input
# ---------------------------------------------------------------------------
@router.post("/process")
@limiter.limit("20/minute")
async def process_json(
    request: Request,
    payload: DataPayload,
    format: Literal["json", "csv", "excel"] = Query("json"),
    limit: Optional[int] = Query(None, ge=1, description="Process only first N rows"),
    x_groq_api_key: Optional[str] = Header(None),
):
    """Accept JSON data, run the full validate → clean → score pipeline."""
    start = time.perf_counter()
    try:
        df = pd.DataFrame(payload.data)
    except Exception as exc:
        raise ProcessingError(f"Failed to parse input data: {exc}") from exc

    ai_service = GroqAIService(api_key=x_groq_api_key) if payload.options.use_ai else None
    return await asyncio.to_thread(_run_pipeline, df, payload.options, format, limit, start, ai_service)


# ---------------------------------------------------------------------------
# Process — file input
# ---------------------------------------------------------------------------
@router.post("/process/file")
@limiter.limit("10/minute")
async def process_file(
    request: Request,
    files: list[UploadFile] = File(...),
    options: str = Form("{}"),
    format: Literal["json", "csv", "excel"] = Query("json"),
    limit: Optional[int] = Query(None, ge=1, description="Process only first N rows"),
    x_groq_api_key: Optional[str] = Header(None),
):
    """Upload multiple files and run the full validate → clean → score pipeline.
    
    If multiple files are provided, they are merged based on common column names.
    """
    start = time.perf_counter()
    
    dfs = []
    for file in files:
        df = await file_handler.read_upload(file)
        dfs.append(df)

    merged_df = _merge_dfs(dfs)

    try:
        opts = CleaningOptions(**json.loads(options))
    except Exception:
        opts = CleaningOptions()

    ai_service = GroqAIService(api_key=x_groq_api_key) if opts.use_ai else None
    return await asyncio.to_thread(_run_pipeline, merged_df, opts, format, limit, start, ai_service)


# ---------------------------------------------------------------------------
# Shared pipeline
# ---------------------------------------------------------------------------
def _run_pipeline(
    df: pd.DataFrame,
    options: CleaningOptions,
    fmt: str,
    limit: int | None,
    start: float,
    ai_service: Optional[GroqAIService] = None,
):
    """Execute validate → clean → score and return the appropriate format."""
    from app.services.validator import DataValidator # local import to avoid circulars if any
    validator = DataValidator()
    
    # Before scores
    quality_before = validator.compute_quality_score(df)
    validation_report = validator.validate(df)

    # Clean
    cleaned_df, cleaning_report = cleaner.clean(df, options, limit=limit, ai_service=ai_service)

    # After scores
    quality_after = validator.compute_quality_score(cleaned_df)

    # AI Summary & Profile
    ai_summary = None
    ai_profile = None
    if options.use_ai and ai_service:
        try:
            # Generate summary of what was cleaned
            ai_summary = ai_service.generate_cleaning_summary(
                cleaning_report.model_dump(),
                quality_before.model_dump(),
                quality_after.model_dump()
            )
            # Also generate a profile of the final cleaned data
            ai_profile = ai_service.profile_dataset(cleaned_df)
        except Exception as exc:
            logger.warning("Failed to generate AI cleaning insights: %s", exc)

    elapsed = round((time.perf_counter() - start) * 1000, 2)

    # --- Return based on format ---
    if fmt == "csv":
        buf = file_handler.to_csv(cleaned_df)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cleaned_data.csv"},
        )
    if fmt == "excel":
        buf = file_handler.to_excel(cleaned_df)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=cleaned_data.xlsx"},
        )

    # JSON (default)
    data = json.loads(cleaned_df.to_json(orient="records", date_format="iso"))
    return ProcessResult(
        validation=validation_report,
        cleaning=cleaning_report,
        quality_score_before=quality_before,
        quality_score_after=quality_after,
        data=data,
        processing_time_ms=elapsed,
        ai_summary=ai_summary,
        ai_profile=ai_profile,
    )
