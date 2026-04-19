"""AI-powered routes for suggestions and standardization."""

from __future__ import annotations

import asyncio
import pandas as pd
from fastapi import APIRouter, Header, HTTPException, Request
from typing import Optional

from app.limiter import limiter

from app.models.requests import AIRequest
from app.services.ai_service import GroqAIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI Integration"])


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_data(
    request: Request,
    payload: AIRequest,
    x_groq_api_key: Optional[str] = Header(None)
):
    """Unified endpoint to analyze data using Groq AI.
    
    Actions:
    - `suggest`: Returns a list of cleaning suggestions.
    - `profile`: Returns a natural-language data quality summary.
    - `standardize`: Normalizes messy categorical values.
    """
    ai_service = GroqAIService(api_key=x_groq_api_key)

    if payload.action in ("suggest", "profile"):
        if not payload.data:
            raise HTTPException(status_code=400, detail="Data payload is required for suggest/profile actions.")
        df = pd.DataFrame(payload.data)
        
        if payload.action == "suggest":
            return await asyncio.to_thread(ai_service.suggest_fixes, df)
        elif payload.action == "profile":
            return await asyncio.to_thread(ai_service.profile_dataset, df)
            
    elif payload.action == "standardize":
        if not payload.values:
            raise HTTPException(status_code=400, detail="Values are required for standardize action.")
        return await asyncio.to_thread(ai_service.standardize_column, payload.values, payload.context)
