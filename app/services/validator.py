"""Data validation and quality scoring service."""

from __future__ import annotations

import logging
from typing import Literal

import pandas as pd

from app.models.responses import DataQualityScore, ValidationReport

logger = logging.getLogger(__name__)


class DataValidator:
    """Service class for validating and scoring DataFrames."""

    @staticmethod
    def _letter_grade(score: float) -> Literal["A", "B", "C", "D", "F"]:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"

    @staticmethod
    def _null_score(df: pd.DataFrame) -> float:
        """100 means no nulls. 0 means every cell is null."""
        total_cells = df.shape[0] * df.shape[1]
        if total_cells == 0:
            return 100.0
        total_nulls = int(df.isnull().sum().sum())
        return round(100 * (1 - total_nulls / total_cells), 2)

    @staticmethod
    def _duplicate_score(df: pd.DataFrame) -> float:
        """100 means no duplicate rows."""
        if len(df) == 0:
            return 100.0
        dup_count = int(df.duplicated().sum())
        return round(100 * (1 - dup_count / len(df)), 2)

    @staticmethod
    def _consistency_score(df: pd.DataFrame) -> float:
        """Measures how consistently typed each column is."""
        if df.empty or df.shape[1] == 0:
            return 100.0

        col_scores: list[float] = []
        for col in df.columns:
            non_null = df[col].dropna()
            if non_null.empty:
                col_scores.append(100.0)
                continue
            type_counts = non_null.map(type).value_counts()
            dominant = type_counts.iloc[0]
            col_scores.append(round(100 * dominant / len(non_null), 2))

        return round(sum(col_scores) / len(col_scores), 2)

    def compute_quality_score(self, df: pd.DataFrame) -> DataQualityScore:
        """Compute a weighted quality score for a DataFrame."""
        ns = self._null_score(df)
        ds = self._duplicate_score(df)
        cs = self._consistency_score(df)
        overall = round(ns * 0.4 + ds * 0.3 + cs * 0.3, 2)
        return DataQualityScore(
            overall=overall,
            null_score=ns,
            duplicate_score=ds,
            consistency_score=cs,
            grade=self._letter_grade(overall),
        )

    def _detect_issues(self, df: pd.DataFrame) -> list[str]:
        """Generate human-readable issue descriptions."""
        issues: list[str] = []
        total_cells = df.shape[0] * df.shape[1]

        # Null issues
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        if not cols_with_nulls.empty:
            total_nulls = int(cols_with_nulls.sum())
            pct = round(100 * total_nulls / total_cells, 1) if total_cells else 0
            issues.append(
                f"{total_nulls} null values found across {len(cols_with_nulls)} "
                f"column(s) ({pct}% of all cells)"
            )

        # Duplicate issues
        dup_count = int(df.duplicated().sum())
        if dup_count:
            issues.append(f"{dup_count} duplicate row(s) detected")

        # Type consistency
        for col in df.columns:
            non_null = df[col].dropna()
            if non_null.empty:
                issues.append(f"Column '{col}' is entirely null")
                continue
            types = non_null.map(type).unique()
            if len(types) > 1:
                type_names = [t.__name__ for t in types]
                issues.append(f"Column '{col}' has mixed types: {', '.join(type_names)}")

        # Whitespace
        for col in df.select_dtypes(include="object").columns:
            stripped = df[col].dropna().astype(str)
            has_leading_trailing = (stripped != stripped.str.strip()).any()
            if has_leading_trailing:
                issues.append(f"Column '{col}' has values with leading/trailing whitespace")

        return issues

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Run full validation on a DataFrame and return a report."""
        logger.info("Validating dataset with %d rows × %d columns", *df.shape)

        null_counts = {col: int(v) for col, v in df.isnull().sum().items() if v > 0}
        column_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
        dup_count = int(df.duplicated().sum())
        issues = self._detect_issues(df)
        quality = self.compute_quality_score(df)

        report = ValidationReport(
            total_rows=len(df),
            total_columns=len(df.columns),
            null_counts=null_counts,
            duplicate_row_count=dup_count,
            column_types=column_types,
            issues=issues,
            quality_score=quality,
        )
        logger.info(
            "Validation complete — score %.1f (%s), %d issue(s)",
            quality.overall,
            quality.grade,
            len(issues),
        )
        return report
