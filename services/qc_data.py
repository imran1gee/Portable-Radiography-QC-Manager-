
import json
from pathlib import Path
from datetime import datetime

from services.app_paths import QC_SESSION

DATA_FILE = QC_SESSION


def save_qc_data(section, values):
    """Save one QC section without deleting other sections."""

    data = load_qc_data()

    data[section] = {
        "values": values,
        "updated_at": datetime.now().isoformat()
    }

    temporary_file = DATA_FILE.with_suffix(".tmp")

    with open(temporary_file, "w") as file:
        json.dump(data, file, indent=4)

    temporary_file.replace(DATA_FILE)


def load_qc_data():
    """Load previously saved QC measurements."""

    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r") as file:
        return json.load(file)


def get_qc_section(section):
    """Retrieve one QC section."""

    data = load_qc_data()
    return data.get(section, {}).get("values", {})
