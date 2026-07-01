"""Excel analysis & dataset validation UI (Phase 6).

Upload an Excel/CSV file and either profile the workbook or run a data-quality
assessment for AI-training suitability. Deterministic — works with no API key.
"""

from __future__ import annotations

import streamlit as st

from audit_assistant.core.logging import get_logger
from audit_assistant.domain.models import FileType
from audit_assistant.infrastructure.parsers.base import detect_file_type
from audit_assistant.services.data_loading import load_dataframes

log = get_logger(__name__)


def _score_color(score: int) -> str:
    return "green" if score >= 80 else "orange" if score >= 60 else "red"


def _render_workbook(container, filename: str, data: bytes, file_type: FileType) -> None:
    report = container.excel_service.analyze(filename=filename, data=data, file_type=file_type)
    for sheet in report.sheets:
        with st.expander(f"📄 {sheet.name} — {sheet.rows} rows × {sheet.columns} cols", expanded=True):
            cols = st.columns(3)
            cols[0].metric("Duplicate rows", sheet.duplicate_rows)
            cols[1].metric("Formula cells", sheet.formula_cells)
            cols[2].metric("Columns", sheet.columns)
            if sheet.issues:
                st.warning("**Issues:**\n" + "\n".join(f"- {i}" for i in sheet.issues))
            st.dataframe(
                [
                    {
                        "column": p.name, "dtype": p.dtype, "missing%": p.missing_pct,
                        "unique": p.unique, "outliers": p.outliers,
                        "min": p.minimum, "max": p.maximum, "mean": p.mean,
                    }
                    for p in sheet.column_profiles
                ],
                use_container_width=True,
            )
    if report.cross_sheet_notes:
        st.subheader("🔗 Cross-sheet comparison")
        for note in report.cross_sheet_notes:
            st.markdown(f"- {note}")


def _render_dataset(container, data: bytes, file_type: FileType) -> None:
    sheets = load_dataframes(data, file_type)
    sheet_name = st.selectbox("Sheet to validate", list(sheets.keys())) if len(sheets) > 1 \
        else next(iter(sheets))
    df = sheets[sheet_name]

    target = st.selectbox(
        "Target/label column (optional — for supervised-learning checks)",
        ["(none)"] + [str(c) for c in df.columns],
    )
    target_col = None if target == "(none)" else target

    if not st.button("🔬 Validate dataset"):
        return

    report = container.dataset_service.validate(df, target=target_col)
    color = _score_color(report.quality_score)
    st.markdown(f"## Quality score: :{color}[**{report.quality_score}/100 (grade {report.grade})**]")
    st.markdown(f"**Verdict:** {report.suitability}")

    st.markdown("**Dimension scores**")
    st.dataframe([report.dimension_scores], use_container_width=True)

    def _bullets(title: str, items: list[str], icon: str) -> None:
        if items:
            st.markdown(f"**{icon} {title}**")
            for it in items:
                st.markdown(f"- {it}")

    c1, c2 = st.columns(2)
    with c1:
        _bullets("Strengths", report.strengths, "✅")
        _bullets("Preprocessing", report.preprocessing, "🧹")
        _bullets("Feature engineering", report.feature_engineering, "🛠️")
    with c2:
        _bullets("Weaknesses", report.weaknesses, "⚠️")
        _bullets("Recommendations", report.recommendations, "💡")


def render_analysis(container) -> None:
    st.subheader("📊 Excel analysis & dataset validation")
    st.caption("Profile a workbook or assess a dataset's quality for AI training. No API key needed.")

    upload = st.file_uploader(
        "Upload an Excel or CSV file", type=["xlsx", "xls", "csv"], key="analysis_upload"
    )
    if not upload:
        st.info("Upload a spreadsheet to analyse.")
        return

    data = upload.getvalue()
    try:
        file_type = detect_file_type(upload.name)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return

    mode = st.radio("Mode", ["Workbook profile", "Dataset quality validation"], horizontal=True)
    try:
        if mode == "Workbook profile":
            _render_workbook(container, upload.name, data, file_type)
        else:
            _render_dataset(container, data, file_type)
    except Exception as exc:  # noqa: BLE001
        log.exception("Analysis failed")
        st.error(f"Analysis failed: {exc}")
