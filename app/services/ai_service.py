"""Groq LLM integration for intelligent data cleaning suggestions."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import pandas as pd

from app.config import settings
from app.errors import AIServiceUnavailableError
from app.models.responses import AISuggestion, AIStandardizeResult

logger = logging.getLogger(__name__)


class GroqAIService:
    """Service class for AI-powered dataset analysis using Groq."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.GROQ_API_KEY
        
        # If we have no key provided directly OR via environment
        if not key:
            raise AIServiceUnavailableError()
            
        from groq import Groq  # lazy import
        self.client = Groq(api_key=key)

    def _chat(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant message."""
        response = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    def _clean_response(self, text: str) -> str:
        """Sanitize AI response by removing markdown code blocks and excess whitespace."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove ```json or ``` at the start
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove ``` at the end
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    @staticmethod
    def _df_sample(df: pd.DataFrame, n: int = 5) -> str:
        """Return a compact string representation of the first *n* rows."""
        return df.head(n).to_csv(index=False)

    def suggest_fixes(self, df: pd.DataFrame) -> list[AISuggestion]:
        """Analyze a dataset sample and return AI-generated cleaning suggestions."""
        logger.info("Requesting AI suggestions for %d-col dataset", len(df.columns))

        system = (
            "You are a data quality analyst. Given a CSV sample, identify data issues "
            "and suggest specific cleaning actions. Respond ONLY with a JSON array of "
            "objects with keys: column, issue, suggestion, confidence (0-1). "
            "No markdown, no explanation — just the JSON array."
        )
        user = f"Dataset sample:\n```\n{self._df_sample(df)}\n```\nTotal rows: {len(df)}"

        raw = self._chat(system, user)
        clean_raw = self._clean_response(raw)
        try:
            items = json.loads(clean_raw)
            return [AISuggestion(**item) for item in items]
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to parse AI suggestions: %s", exc)
            return []

    def standardize_column(self, values: list[str], context: str = "") -> AIStandardizeResult:
        """Use the LLM to normalize messy categorical values."""
        logger.info("Requesting AI standardization for %d values", len(values))

        ctx = f" Context: {context}." if context else ""
        system = (
            "You are a data standardization expert. Given a list of messy values, "
            "produce a canonical mapping.{ctx} Respond ONLY with a JSON object with keys: "
            "standardized_values (list), mapping (dict of original→standard). "
            "No markdown, no explanation — just JSON."
        ).format(ctx=ctx)
        user = f"Values:\n{json.dumps(values)}"

        raw = self._chat(system, user)
        clean_raw = self._clean_response(raw)
        try:
            result = json.loads(clean_raw)
            return AIStandardizeResult(
                original_values=values,
                standardized_values=result.get("standardized_values", []),
                mapping=result.get("mapping", {}),
            )
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to parse AI standardization: %s", exc)
            return AIStandardizeResult(
                original_values=values,
                standardized_values=values,
                mapping={},
            )

    def profile_dataset(self, df: pd.DataFrame) -> str:
        """Generate a natural-language data quality summary."""
        logger.info("Requesting AI profile for %d-row dataset", len(df))

        system = (
            "You are a technical data analyst. Analyze the cleaned dataset and provide a factual, "
            "concise technical report on its state. "
            "Describe data patterns, column relationships, and identify any significant clusters or outliers. "
            "Keep it purely technical and data-centric. Avoid generic advice or 'data governance' talk. "
            "Use markdown bolding for emphasis and lists for readability."
        )
        stats = (
            f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
            f"Null counts: {dict(df.isnull().sum())}\n"
            f"Duplicates: {int(df.duplicated().sum())}\n"
            f"Column types: {dict(df.dtypes.astype(str))}"
        )
        user = f"Dataset sample:\n```\n{self._df_sample(df)}\n```\n\nStats:\n{stats}"

        return self._chat(system, user)

    def suggest_column_renames(self, df: pd.DataFrame) -> dict[str, str]:
        """Suggest better names for 'Unnamed' or messy columns."""
        logger.info("Requesting AI column renames")
        system = (
            "Analyze the dataset sample and suggest better names for columns, "
            "especially those named 'Unnamed: X' or which are clearly messy. "
            "Return ONLY a JSON object mapping old_name -> new_name. "
            "If a name is already good, exclude it from the mapping."
        )
        user = f"Sample:\n{self._df_sample(df)}"
        raw = self._chat(system, user)
        try:
            return json.loads(self._clean_response(raw))
        except Exception:
            return {}

    def generate_cleaning_summary(self, report: dict, score_before: dict, score_after: dict) -> str:
        """Write a concise summary of what was cleaned and why."""
        logger.info("Requesting AI cleaning summary")
        system = (
            "You are a data cleaning engine. Factually summarize the transformations performed in this execution. "
            "List exactly what was changed (nulls handled, columns renamed, duplicates removed). "
            "Keep it concise, objective, and technical. No advice, just execution facts. "
            "Use markdown for lists."
        )
        user = (
            f"Cleaning Report: {json.dumps(report)}\n"
            f"Quality Before: {json.dumps(score_before)}\n"
            f"Quality After: {json.dumps(score_after)}"
        )
        return self._chat(system, user)
