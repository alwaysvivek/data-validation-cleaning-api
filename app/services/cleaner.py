"""Pandas-based data cleaning engine."""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ai_service import GroqAIService

import pandas as pd

from app.models.requests import CleaningOptions
from app.models.responses import CleaningReport

logger = logging.getLogger(__name__)


class DataCleaner:
    """Service class for cleaning DataFrames."""

    @staticmethod
    def _standardize_name(name: str) -> str:
        """Convert a column name to snake_case."""
        s = name.strip()
        s = re.sub(r"[^\w\s]", "", s)   # remove special chars
        s = re.sub(r"\s+", "_", s)       # spaces → underscores
        return s.lower()

    def clean(
        self,
        df: pd.DataFrame,
        options: CleaningOptions,
        limit: Optional[int] = None,
        ai_service: Optional[GroqAIService] = None,
    ) -> Tuple[pd.DataFrame, CleaningReport]:
        """Apply cleaning operations and return the cleaned DataFrame + report."""

        rows_before = len(df)
        columns_renamed: dict[str, str] = {}
        nulls_handled = 0

        # ---- 1. Row limit --------------------------------------------------
        if limit is not None and limit > 0:
            df = df.head(limit).copy()
            logger.info("Limited to first %d rows (had %d)", limit, rows_before)
            rows_before = len(df)
        else:
            df = df.copy()

        # ---- 2. Strip whitespace -------------------------------------------
        if options.strip_whitespace:
            str_cols = df.select_dtypes(include="object").columns
            for col in str_cols:
                df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA)
            logger.info("Stripped whitespace on %d string column(s)", len(str_cols))

        # ---- 2.5 AI-Powered Renaming ---------------------------------------
        if options.use_ai and ai_service:
            ai_renames = ai_service.suggest_column_renames(df)
            if ai_renames:
                df.rename(columns=ai_renames, inplace=True)
                columns_renamed.update(ai_renames)
                logger.info("AI suggested %d column rename(s)", len(ai_renames))

        # ---- 3. Standardize column names -----------------------------------
        if options.standardize_columns:
            new_names = {col: self._standardize_name(col) for col in df.columns}
            renamed = {k: v for k, v in new_names.items() if k != v}
            if renamed:
                df.rename(columns=new_names, inplace=True)
                columns_renamed = renamed
                logger.info("Renamed %d column(s)", len(renamed))

        # ---- 4. Remove empty rows ------------------------------------------
        if options.remove_empty_rows:
            before = len(df)
            df.dropna(how="all", inplace=True)
            removed = before - len(df)
            if removed:
                logger.info("Removed %d fully-empty row(s)", removed)

        # ---- 5. Handle nulls -----------------------------------------------
        null_count_before = int(df.isnull().sum().sum())
        strategy = options.handle_nulls

        if strategy == "drop":
            df.dropna(inplace=True)
        elif strategy == "fill_mean":
            num_cols = df.select_dtypes(include="number").columns
            if not num_cols.empty:
                df[num_cols] = df[num_cols].fillna(df[num_cols].mean())
            str_cols = df.select_dtypes(include="object").columns
            if not str_cols.empty:
                df[str_cols] = df[str_cols].fillna("")
        elif strategy == "fill_median":
            num_cols = df.select_dtypes(include="number").columns
            if not num_cols.empty:
                df[num_cols] = df[num_cols].fillna(df[num_cols].median())
            str_cols = df.select_dtypes(include="object").columns
            if not str_cols.empty:
                df[str_cols] = df[str_cols].fillna("")
        elif strategy == "fill_mode":
            for col in df.columns:
                mode_vals = df[col].mode()
                if not mode_vals.empty:
                    df[col] = df[col].fillna(mode_vals.iloc[0])
        elif strategy == "fill_empty":
            str_cols = df.select_dtypes(include="object").columns
            if not str_cols.empty:
                df[str_cols] = df[str_cols].fillna("")

        null_count_after = int(df.isnull().sum().sum())
        nulls_handled = null_count_before - null_count_after
        if strategy != "none":
            logger.info("Null strategy '%s': handled %d null(s)", strategy, nulls_handled)

        # ---- 6. Remove duplicates ------------------------------------------
        dups_before = int(df.duplicated().sum())
        if options.remove_duplicates and dups_before > 0:
            df.drop_duplicates(inplace=True)
            logger.info("Removed %d duplicate row(s)", dups_before)

        # ---- 7. Auto-convert dates -----------------------------------------
        if options.convert_dates:
            converted = 0
            for col in df.select_dtypes(include="object").columns:
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                    # Only convert if ≥50 % of non-null values parsed successfully
                    non_null = df[col].dropna()
                    if non_null.empty:
                        continue
                    success_rate = parsed.notna().sum() / len(non_null)
                    if success_rate >= 0.5:
                        df[col] = parsed
                        converted += 1
                except Exception:
                    pass
            if converted:
                logger.info("Auto-converted %d column(s) to datetime", converted)

        # Reset index after all transformations
        df.reset_index(drop=True, inplace=True)

        report = CleaningReport(
            rows_before=rows_before,
            rows_after=len(df),
            duplicates_removed=dups_before if options.remove_duplicates else 0,
            nulls_handled=nulls_handled,
            columns_renamed=columns_renamed,
        )
        logger.info("Cleaning complete: %d → %d rows", rows_before, len(df))
        return df, report
