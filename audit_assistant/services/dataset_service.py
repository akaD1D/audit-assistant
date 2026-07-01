"""Dataset quality validation for AI-training suitability.

Deterministic, heuristic checks (pandas/numpy) producing a quality score plus
strengths, weaknesses, and actionable recommendations. No LLM — so the verdict
is reproducible and explainable. The chat layer can narrate the report, but the
findings come from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

# Column names that warrant a fairness/bias review if present as features.
_SENSITIVE = {"gender", "sex", "race", "ethnicity", "nationality", "religion",
              "age", "disability", "marital_status"}


@dataclass(slots=True)
class DatasetReport:
    rows: int
    columns: int
    quality_score: int
    grade: str
    dimension_scores: dict[str, int] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    preprocessing: list[str] = field(default_factory=list)
    feature_engineering: list[str] = field(default_factory=list)
    suitability: str = ""


def _grade(score: int) -> str:
    return ("A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70
            else "D" if score >= 60 else "F")


class DatasetValidationService:
    """Evaluates a DataFrame for data quality and training readiness."""

    def validate(self, df: pd.DataFrame, *, target: str | None = None) -> DatasetReport:
        n_rows, n_cols = df.shape
        report = DatasetReport(rows=n_rows, columns=n_cols, quality_score=0, grade="F")
        if n_rows == 0 or n_cols == 0:
            report.weaknesses.append("Dataset is empty.")
            report.suitability = "Not usable — the dataset has no data."
            return report

        dims = report.dimension_scores
        dims["completeness"] = self._completeness(df, report)
        dims["uniqueness"] = self._duplicates(df, report)
        dims["consistency"] = self._consistency(df, report)
        dims["feature_usefulness"] = self._usefulness(df, report, target)
        dims["size_adequacy"] = self._size(df, report)
        if target and target in df.columns:
            dims["class_balance"] = self._balance(df, target, report)
            self._leakage(df, target, report)
        self._outliers(df, report)
        self._bias(df, report)
        self._feature_ideas(df, report, target)

        score = int(round(sum(dims.values()) / len(dims)))
        report.quality_score = score
        report.grade = _grade(score)
        report.suitability = self._verdict(score, n_rows, target)
        log.info("Validated dataset: score=%d grade=%s", score, report.grade)
        return report

    # --- dimension checks ----------------------------------------------------
    def _completeness(self, df: pd.DataFrame, r: DatasetReport) -> int:
        missing_pct = df.isna().mean() * 100
        avg_missing = float(missing_pct.mean())
        high = missing_pct[missing_pct >= 30].index.tolist()
        if avg_missing < 1:
            r.strengths.append("Very few missing values.")
        if high:
            r.weaknesses.append(f"High missingness (≥30%) in: {', '.join(map(str, high))}.")
            r.preprocessing.append(
                f"Impute or drop high-missing columns: {', '.join(map(str, high))}."
            )
        elif avg_missing > 0:
            r.preprocessing.append("Impute remaining missing values (mean/median/mode or model-based).")
        return int(max(0, 100 - avg_missing * 2))

    def _duplicates(self, df: pd.DataFrame, r: DatasetReport) -> int:
        dup = int(df.duplicated().sum())
        pct = dup / len(df) * 100
        if dup == 0:
            r.strengths.append("No duplicate rows.")
        else:
            r.weaknesses.append(f"{dup} duplicate row(s) ({pct:.1f}%).")
            r.preprocessing.append("Remove duplicate rows (df.drop_duplicates()).")
        return int(max(0, 100 - pct * 3))

    def _consistency(self, df: pd.DataFrame, r: DatasetReport) -> int:
        penalty = 0
        for col in df.select_dtypes(include="object").columns:
            values = df[col].dropna().astype(str)
            if values.empty:
                continue
            if (values != values.str.strip()).any():
                penalty += 5
                r.weaknesses.append(f"Leading/trailing whitespace in '{col}'.")
                r.preprocessing.append(f"Strip whitespace in '{col}'.")
            lowered = values.str.lower().str.strip()
            if lowered.nunique() < values.nunique():
                penalty += 5
                r.weaknesses.append(f"Inconsistent casing creates duplicate categories in '{col}'.")
                r.preprocessing.append(f"Standardise casing/categories in '{col}'.")
        if df.replace([np.inf, -np.inf], np.nan).isna().sum().sum() > df.isna().sum().sum():
            penalty += 5
            r.weaknesses.append("Infinite values present.")
        if penalty == 0:
            r.strengths.append("Consistent formatting across text columns.")
        return int(max(0, 100 - penalty))

    def _usefulness(self, df: pd.DataFrame, r: DatasetReport, target: str | None) -> int:
        n = len(df)
        constant = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
        id_like = [
            c for c in df.columns
            if c != target and df[c].nunique(dropna=True) == n and n > 1
        ]
        high_card = [
            c for c in df.select_dtypes(include="object").columns
            if c not in id_like and df[c].nunique(dropna=True) > 0.5 * n and n > 10
        ]
        if constant:
            r.weaknesses.append(f"Constant (zero-information) column(s): {', '.join(map(str, constant))}.")
            r.preprocessing.append(f"Drop constant columns: {', '.join(map(str, constant))}.")
        if id_like:
            r.weaknesses.append(
                f"Identifier-like column(s) unique per row: {', '.join(map(str, id_like))} "
                "(no predictive value; possible leakage)."
            )
            r.preprocessing.append(f"Drop or set aside ID columns: {', '.join(map(str, id_like))}.")
        if high_card:
            r.recommendations.append(
                f"High-cardinality text column(s): {', '.join(map(str, high_card))} — "
                "consider target/frequency encoding or grouping rare levels."
            )
        penalty = (len(constant) + len(id_like)) / max(1, df.shape[1]) * 100
        if not constant and not id_like:
            r.strengths.append("No constant or identifier-only columns.")
        return int(max(0, 100 - penalty))

    def _size(self, df: pd.DataFrame, r: DatasetReport) -> int:
        n = len(df)
        if n < 50:
            r.weaknesses.append(f"Very small dataset ({n} rows) — high overfitting risk.")
            r.recommendations.append("Collect more data or use simple models / cross-validation.")
            return 30
        if n < 500:
            r.recommendations.append("Modest row count — prefer regularised/simple models and CV.")
            return 65
        r.strengths.append(f"Adequate row count ({n:,}).")
        return 90

    def _balance(self, df: pd.DataFrame, target: str, r: DatasetReport) -> int:
        counts = df[target].value_counts(normalize=True)
        if counts.empty:
            return 50
        majority = float(counts.iloc[0]) * 100
        minority = float(counts.iloc[-1]) * 100
        if majority >= 90:
            r.weaknesses.append(
                f"Severe class imbalance in '{target}' (majority {majority:.1f}%)."
            )
            r.preprocessing.append(
                "Address imbalance: resampling (SMOTE/undersampling) or class weights."
            )
            return 40
        if majority >= 75:
            r.recommendations.append(
                f"Moderate class imbalance in '{target}' (majority {majority:.1f}%) — "
                "consider class weights."
            )
            return 70
        r.strengths.append(f"Reasonably balanced target '{target}'.")
        return 90

    def _leakage(self, df: pd.DataFrame, target: str, r: DatasetReport) -> None:
        num = df.select_dtypes(include="number")
        if target not in num.columns or num.shape[1] < 2:
            return
        corr = num.corr(numeric_only=True)[target].drop(labels=[target], errors="ignore")
        leaky = corr[corr.abs() > 0.95].index.tolist()
        if leaky:
            r.weaknesses.append(
                f"Possible target leakage: {', '.join(map(str, leaky))} almost perfectly "
                f"correlated with '{target}'."
            )
            r.recommendations.append(
                f"Investigate {', '.join(map(str, leaky))} for leakage before training."
            )

    def _outliers(self, df: pd.DataFrame, r: DatasetReport) -> None:
        flagged = []
        for col in df.select_dtypes(include="number").columns:
            s = df[col].dropna()
            if len(s) < 4:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
            if out:
                flagged.append(f"{col} ({out})")
        if flagged:
            r.recommendations.append(f"Review/scale numeric outliers in: {', '.join(flagged)}.")

    def _bias(self, df: pd.DataFrame, r: DatasetReport) -> None:
        present = [c for c in df.columns if str(c).strip().lower() in _SENSITIVE]
        if present:
            r.recommendations.append(
                f"Sensitive attribute(s) present ({', '.join(map(str, present))}) — perform a "
                "fairness/bias review and consider excluding them from training."
            )

    def _feature_ideas(self, df: pd.DataFrame, r: DatasetReport, target: str | None) -> None:
        if any(pd.api.types.is_datetime64_any_dtype(df[c]) for c in df.columns) or any(
            "date" in str(c).lower() for c in df.columns
        ):
            r.feature_engineering.append("Derive features from dates (year, month, weekday, recency).")
        if df.select_dtypes(include="number").shape[1] >= 2:
            r.feature_engineering.append("Create ratios/differences between related numeric columns.")
        if df.select_dtypes(include="object").shape[1] >= 1:
            r.feature_engineering.append("Encode categoricals (one-hot for low-, target-encode for high-cardinality).")
        r.feature_engineering.append("Scale/normalise numeric features for distance/gradient-based models.")

    @staticmethod
    def _verdict(score: int, n_rows: int, target: str | None) -> str:
        base = ""
        if score >= 80:
            base = "✅ Suitable for AI training with minor preprocessing."
        elif score >= 60:
            base = "⚠️ Usable, but clean and preprocess it first (see recommendations)."
        else:
            base = "❌ Not recommended for training until the major issues are resolved."
        if not target:
            base += " No target column was specified — for supervised learning, define/validate a label."
        return base
