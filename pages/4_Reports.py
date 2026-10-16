import streamlit as st
from pathlib import Path

from services.app_paths import RESOURCE_DIR, USER_DATA_DIR

BUNDLED_LOGO = RESOURCE_DIR / "assets" / "institution_logo.png"
CUSTOM_LOGO = USER_DATA_DIR / "institution_logo.png"

LOGO_PATH = CUSTOM_LOGO if CUSTOM_LOGO.exists() else BUNDLED_LOGO


from services.excel_export import generate_excel_report

st.title("Generate QC Report")
st.caption("Create an Excel report without using a template.")

st.subheader("Optional Report Images")

logo = st.file_uploader(
    "Institution Logo",
    type=["png", "jpg", "jpeg"],
    key="report_logo",
)


if logo is not None:
    CUSTOM_LOGO.write_bytes(logo.getvalue())
    LOGO_PATH = CUSTOM_LOGO

if LOGO_PATH.exists():
    st.image(str(LOGO_PATH), width=220)
    st.success("Institution logo saved and available for future reports.")

signature = st.file_uploader(
    "Authorized Signature",
    type=["png", "jpg", "jpeg"],
    key="report_signature",
)

st.caption(
    "A signature is included only when explicitly uploaded "
    "for this report. Upload only an authorized signature."
)

if st.button("Generate Excel Report", type="primary"):
    st.session_state.pop("v2_report_bytes", None)
    st.session_state.pop("v2_report_name", None)

    try:
        with st.spinner("Creating Excel report..."):
            output = generate_excel_report(
                logo_bytes=LOGO_PATH.read_bytes() if LOGO_PATH.exists() else None,
                signature_bytes=signature.getvalue() if signature else None,
            )

        st.session_state["v2_report_bytes"] = output.read_bytes()
        st.session_state["v2_report_name"] = output.name

        st.success("Excel report generated successfully.")

    except Exception as error:
        st.error(f"Could not generate report: {error}")

if "v2_report_bytes" in st.session_state:
    st.download_button(
        "Download Excel Report",
        data=st.session_state["v2_report_bytes"],
        file_name=st.session_state["v2_report_name"],
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

st.warning(
    "This is a cover-sheet prototype, not a completed clinical "
    "QC report. State Form and RAD MODE will be added next."
)
