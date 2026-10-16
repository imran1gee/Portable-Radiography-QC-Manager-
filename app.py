import json
from datetime import date, datetime
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Portable Radiography QC Manager",
    page_icon="🩻",
    layout="wide",
)

from services.app_paths import REPORT_INFO
DATA_FILE = REPORT_INFO
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_information():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            st.warning("Could not read previously saved report information.")
    return {}


def save_information(values):
    temporary = DATA_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(values, indent=2))
    temporary.replace(DATA_FILE)


saved = load_information()

st.title("Portable Radiography QC Manager")
st.caption("Facility, Equipment, and Report Information")

with st.form("report_information_form"):

    st.header("Report Information")

    col1, col2 = st.columns(2)

    with col1:
        inspection_date = st.date_input(
            "Survey Date",
            value=date.fromisoformat(
                saved.get("inspection_date", date.today().isoformat())
            ),
        )

    with col2:
        report_number = st.text_input(
            "Report",
            value=saved.get("report_number", ""),
        )

    report_date = st.date_input(
        "Report Date",
        value=date.fromisoformat(saved.get("report_date", date.today().isoformat())),
    )

    st.header("Facility Information")

    col1, col2 = st.columns(2)

    with col1:
        site = st.text_input(
            "Site",
            value=saved.get("site", ""),
        )
        building = st.text_input(
            "Building / Location",
            value=saved.get("building", ""),
        )
        room = st.text_input(
            "Room",
            value=saved.get("room", ""),
        )

    with col2:
        department = st.text_input(
            "Department",
            value=saved.get("department", ""),
        )
        city = st.text_input(
            "City",
            value=saved.get("city", ""),
        )
        street = st.text_input(
            "Street",
            value=saved.get("street", ""),
        )
        facility_id = st.text_input(
            "Facility ID",
            value=saved.get("facility_id", ""),
        )

    st.header("Equipment Information")

    col1, col2 = st.columns(2)

    with col1:
        equipment_type = st.text_input(
            "Equipment Type",
            value=saved.get("equipment_type", "Mobile Rad"),
        )
        manufacturer = st.text_input(
            "Manufacturer",
            value=saved.get("manufacturer", ""),
        )
        model = st.text_input(
            "Model",
            value=saved.get("model", ""),
        )
        serial_number = st.text_input(
            "S/N",
            value=saved.get("serial_number", ""),
        )

    with col2:
        year_of_manufacture = st.text_input(
            "DOM",
            value=saved.get("year_of_manufacture", ""),
        )
        iema_number = st.text_input(
            "IEMA",
            value=saved.get("iema_number", ""),
        )
        ceid = st.text_input(
            "CEID",
            value=saved.get("ceid", ""),
        )
        acr_number = st.text_input(
            "ACR",
            value=saved.get("acr_number", ""),
        )

    st.header("Personnel")

    medical_physicist = st.text_input(
        "Medical Physicist",
        value=saved.get("medical_physicist", ""),
    )

    trainee = st.text_input(
        "Trainee",
        value=saved.get("trainee", ""),
    )

    st.header("Additional RAD MODE Information")

    inspector_options = {
        "Reiser": "1384",
        "Lu": "1319",
        "Kofler": "1740",
    }

    saved_inspector_id = str(saved.get("inspector_id", ""))
    inspector_names = list(inspector_options)
    inspector_index = next(
        (
            i for i, name in enumerate(inspector_names)
            if inspector_options[name] == saved_inspector_id
        ),
        None,
    )

    selected_inspector = st.selectbox(
        "Inspector",
        options=inspector_names,
        index=inspector_index,
        placeholder="Select inspector",
    )

    inspector_id = (
        inspector_options[selected_inspector]
        if selected_inspector is not None else ""
    )

    st.caption(f"Inspector ID: {inspector_id or 'Not selected'}")

    generator_type = st.text_input(
        "Generator Type",
        value=saved.get("generator_type", ""),
        placeholder="e.g. High Freq",
    )

    equipment_options = {
        "Radcal AG Touchpro w/AGDM+ — 55-1701": (
            "Radcal AG Touchpro w/AGDM+",
            "55-1701",
            "2025-10-10",
        ),
        "Radcal AG Touchpro w/AGDM+ — 55-3481": (
            "Radcal AG Touchpro w/AGDM+",
            "55-3481",
            "2026-05-18",
        ),
    }

    saved_serials = [
        x.strip()
        for x in str(saved.get("test_equipment_serial", "")).split(";")
        if x.strip()
    ]

    selected_equipment = st.multiselect(
        "Test Equipment Used",
        options=list(equipment_options),
        default=[
            name for name, details in equipment_options.items()
            if details[1] in saved_serials
        ],
        help="Select one or both instruments.",
    )

    # Calibration dates remain visible inside the Streamlit form.
    # Forms do not rerun when the equipment multiselect changes.
    saved_dates = [
        x.strip()
        for x in str(saved.get("calibration_date", "")).split(";")
    ]

    selected_details = []

    st.caption(
        "Calibration dates for both instruments are shown below. "
        "Only selected equipment will be saved to the report."
    )

    for name, (model_name, serial, default_calibration) in equipment_options.items():
        if serial in saved_serials:
            idx = saved_serials.index(serial)
            initial_date = (
                saved_dates[idx]
                if idx < len(saved_dates) and saved_dates[idx]
                else default_calibration
            )
        else:
            initial_date = default_calibration

        try:
            parsed_date = datetime.strptime(
                initial_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            parsed_date = datetime.strptime(
                default_calibration, "%Y-%m-%d"
            ).date()

        calibration = st.date_input(
            f"Calibration Date — S/N {serial}",
            value=parsed_date,
            key=f"calibration_{serial}",
            format="MM/DD/YYYY",
        )

        if name in selected_equipment:
            selected_details.append(
                (model_name, serial, calibration.isoformat())
            )

    test_equipment = "; ".join(
        item[0] for item in selected_details
    )
    test_equipment_serial = "; ".join(
        item[1] for item in selected_details
    )
    calibration_date = "; ".join(
        item[2] for item in selected_details
    )

    st.header("Comments")

    comments = st.text_area(
        "Comments",
        value=saved.get("comments", ""),
        height=120,
    )

    submitted = st.form_submit_button(
        "Save Report Information",
        type="primary",
    )

if submitted:
    information = dict(saved)
    information.update({
        "inspection_date": inspection_date.isoformat(),
        "report_date": report_date.isoformat(),
        "report_number": report_number,
        "site": site,
        "building": building,
        "room": room,
        "department": department,
        "city": city,
        "street": street,
        "facility_id": facility_id,
        "equipment_type": equipment_type,
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": serial_number,
        "year_of_manufacture": year_of_manufacture,
        "iema_number": iema_number,
        "ceid": ceid,
        "acr_number": acr_number,
        "medical_physicist": medical_physicist,
        "trainee": trainee,
        "comments": comments,
        "inspector_id": inspector_id,
        "generator_type": generator_type,
        "test_equipment": test_equipment,
        "test_equipment_serial": test_equipment_serial,
        "calibration_date": calibration_date,
        "updated_at": datetime.now().isoformat(),
    })

    save_information(information)
    st.success("Report information saved successfully.")
