"""Excel / tabular workbook analysis.

Deterministic profiling of each sheet: shape, per-column types + missing values,
duplicate rows, numeric outliers (IQR), formula cells, and cross-sheet
comparison. Feeds the UI and the report generator (Phase 8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import FileType
from audit_assistant.services.data_loading import count_formula_cells, load_dataframes

log = get_logger(__name__)


@dataclass(slots=True)
class ColumnProfile:
    name: str
    dtype: str
    missing: int
    missing_pct: float
    unique: int
    is_constant: bool
    outliers: int = 0
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None


@dataclass(slots=True)
class SheetReport:
    name: str
    rows: int
    columns: int
    duplicate_rows: int
    formula_cells: int
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkbookReport:
    filename: str
    sheets: list[SheetReport] = field(default_factory=list)
    cross_sheet_notes: list[str] = field(default_factory=list)


def _iqr_outliers(series: pd.Series) -> int:
    clean = series.dropna()
    if len(clean) < 4:
        return 0
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((clean < low) | (clean > high)).sum())


def _profile_column(df: pd.DataFrame, col: str) -> ColumnProfile:
    series = df[col]
    n = len(df)
    missing = int(series.isna().sum())
    unique = int(series.nunique(dropna=True))
    profile = ColumnProfile(
        name=str(col),
        dtype=str(series.dtype),
        missing=missing,
        missing_pct=round(missing / n * 100, 2) if n else 0.0,
        unique=unique,
        is_constant=unique <= 1,
    )
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()
        if not clean.empty:
            profile.minimum = float(clean.min())
            profile.maximum = float(clean.max())
            profile.mean = round(float(clean.mean()), 4)
            profile.outliers = _iqr_outliers(clean)
    return profile


class ExcelAnalysisService:
    """Profiles workbooks and tabular files."""

    def analyze(self, *, filename: str, data: bytes, file_type: FileType) -> WorkbookReport:
        sheets = load_dataframes(data, file_type)
        formula_counts = count_formula_cells(data) if file_type == FileType.XLSX else {}

        report = WorkbookReport(filename=filename)
        for name, df in sheets.items():
            report.sheets.append(self._analyze_sheet(name, df, formula_counts.get(name, 0)))

        report.cross_sheet_notes = self._compare_sheets(sheets)
        log.info("Analysed workbook '%s' (%d sheet(s))", filename, len(report.sheets))
        return report

    def _analyze_sheet(self, name: str, df: pd.DataFrame, formula_cells: int) -> SheetReport:
        duplicate_rows = int(df.duplicated().sum())
        profiles = [_profile_column(df, c) for c in df.columns]

        issues: list[str] = []
        if duplicate_rows:
            issues.append(f"{duplicate_rows} duplicate row(s).")
        constant_cols = [p.name for p in profiles if p.is_constant]
        if constant_cols:
            issues.append(f"Constant column(s): {', '.join(constant_cols)}.")
        high_missing = [p.name for p in profiles if p.missing_pct >= 30]
        if high_missing:
            issues.append(f"Column(s) ≥30% missing: {', '.join(high_missing)}.")
        outlier_cols = [f"{p.name} ({p.outliers})" for p in profiles if p.outliers]
        if outlier_cols:
            issues.append(f"Numeric outliers in: {', '.join(outlier_cols)}.")

        return SheetReport(
            name=name,
            rows=len(df),
            columns=len(df.columns),
            duplicate_rows=duplicate_rows,
            formula_cells=formula_cells,
            column_profiles=profiles,
            issues=issues,
        )

    @staticmethod
    def _compare_sheets(sheets: dict[str, pd.DataFrame]) -> list[str]:
        names = list(sheets.keys())
        if len(names) < 2:
            return []
        notes: list[str] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                cols_a, cols_b = set(sheets[a].columns), set(sheets[b].columns)
                shared = cols_a & cols_b
                if shared:
                    notes.append(
                        f"'{a}' and '{b}' share {len(shared)} column(s): "
                        f"{', '.join(map(str, sorted(map(str, shared))))}. "
                        f"Rows: {len(sheets[a])} vs {len(sheets[b])}."
                    )
        return notes
