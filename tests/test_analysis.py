"""Tests for Excel analysis and dataset validation."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from audit_assistant.domain.models import FileType
from audit_assistant.services.dataset_service import DatasetValidationService
from audit_assistant.services.excel_service import ExcelAnalysisService


@pytest.fixture
def messy_xlsx() -> bytes:
    df = pd.DataFrame(
        {
            "account": ["Cash", "AR", "AR", "Cash"],  # duplicate-ish
            "region": ["N", "N", "N", "N"],  # constant column
            "amount": [100.0, 200.0, None, 100.0],  # missing + potential dup row
        }
    )
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # force an exact duplicate row
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Ledger", index=False)
    return buf.getvalue()


def test_excel_analysis_detects_issues(messy_xlsx) -> None:
    report = ExcelAnalysisService().analyze(
        filename="ledger.xlsx", data=messy_xlsx, file_type=FileType.XLSX
    )
    assert len(report.sheets) == 1
    sheet = report.sheets[0]
    assert sheet.duplicate_rows >= 1
    issues = " ".join(sheet.issues).lower()
    assert "constant" in issues
    # Missing value captured in the column profile (below the 30% "issue" threshold).
    amount_profile = next(p for p in sheet.column_profiles if p.name == "amount")
    assert amount_profile.missing == 1


def test_good_dataset_scores_well() -> None:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "amount": rng.integers(1, 100, 600).astype(float),
            "score": rng.random(600),
            "category": rng.choice(["a", "b", "c"], 600),
            "label": rng.integers(0, 2, 600),
        }
    )
    report = DatasetValidationService().validate(df, target="label")
    assert report.quality_score >= 80
    assert report.grade in {"A", "B"}
    assert "Suitable" in report.suitability


def test_bad_dataset_flags_problems() -> None:
    df = pd.DataFrame(
        {
            "row_id": list(range(30)),  # identifier-like
            "constant": ["x"] * 30,  # constant
            "partly_missing": [1.0] * 10 + [None] * 20,  # 66% missing
            "target": [0] * 28 + [1] * 2,  # severe imbalance
        }
    )
    report = DatasetValidationService().validate(df, target="target")
    assert report.quality_score < 70
    weaknesses = " ".join(report.weaknesses).lower()
    assert "constant" in weaknesses
    assert "identifier" in weaknesses
    assert "imbalance" in weaknesses
    assert report.preprocessing  # actionable steps present


def test_leakage_detection() -> None:
    df = pd.DataFrame({"target": [0, 1] * 50})
    df["leak"] = df["target"] * 10  # perfectly correlated with target
    df["noise"] = np.random.default_rng(1).random(100)
    report = DatasetValidationService().validate(df, target="target")
    assert any("leakage" in w.lower() for w in report.weaknesses)


def test_empty_dataset() -> None:
    report = DatasetValidationService().validate(pd.DataFrame())
    assert report.quality_score == 0
    assert "not usable" in report.suitability.lower()
