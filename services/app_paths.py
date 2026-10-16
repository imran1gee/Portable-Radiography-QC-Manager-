from pathlib import Path

APP_NAME = "Portable Radiography QC Manager V2"

RESOURCE_DIR = Path(__file__).resolve().parent.parent

USER_DATA_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / APP_NAME
)

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

REPORT_INFO = USER_DATA_DIR / "report_information.json"
QC_SESSION = USER_DATA_DIR / "qc_session.json"

REPORTS_DIR = USER_DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
