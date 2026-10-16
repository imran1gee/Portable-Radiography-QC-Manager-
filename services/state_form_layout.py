import math
import json
from pathlib import Path
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, Color
from openpyxl.utils.cell import range_boundaries

LAYOUT = Path(__file__).parent / "layouts" / "state_form.json"

def make_color(d):
    if not d or not d.get("type"):
        return None
    t = d["type"]
    kw = {"type": t}
    if t == "rgb" and isinstance(d.get("rgb"), str) and len(d["rgb"]) == 8:
        kw["rgb"] = d["rgb"]
    elif t == "indexed" and d.get("indexed") is not None:
        kw["indexed"] = d["indexed"]
    elif t == "theme" and d.get("theme") is not None:
        kw["theme"] = d["theme"]
    elif t == "auto":
        kw["auto"] = bool(d.get("auto"))
    else:
        return None
    kw["tint"] = d.get("tint") or 0
    return Color(**kw)

def make_side(d):
    return Side(style=d.get("style"), color=make_color(d.get("color")))

def apply_style(cell, s):
    f = s["font"]
    cell.font = Font(
        name=f.get("name"),
        size=f.get("sz"),
        bold=f.get("b"),
        italic=f.get("i"),
        underline=f.get("u"),
        strike=f.get("strike"),
        color=make_color(f.get("color")),
        vertAlign=f.get("vertAlign"),
    )

    a = s["alignment"]
    cell.alignment = Alignment(
        horizontal=a.get("horizontal"),
        vertical=a.get("vertical"),
        textRotation=a.get("textRotation") or 0,
        wrapText=a.get("wrapText"),
        shrinkToFit=a.get("shrinkToFit"),
        indent=a.get("indent") or 0,
    )

    fill = s["fill"]
    cell.fill = PatternFill(
        patternType=fill.get("patternType"),
        fgColor=make_color(fill.get("fgColor")) or Color(rgb="00000000"),
        bgColor=make_color(fill.get("bgColor")) or Color(rgb="00000000"),
    )

    b = s["border"]
    cell.border = Border(**{
        side: make_side(b[side])
        for side in ("left", "right", "top", "bottom")
    })
    cell.number_format = s.get("number_format") or "General"

def build_state_form(ws):
    data = json.loads(LAYOUT.read_text())

    for col, spec in data["columns"].items():
        ws.column_dimensions[col].width = spec["width"]
        ws.column_dimensions[col].hidden = spec["hidden"]

    for row, spec in data["rows"].items():
        ws.row_dimensions[int(row)].height = spec["height"]
        ws.row_dimensions[int(row)].hidden = spec["hidden"]

    # Recreate formatting first.
    for address, spec in data["cells"].items():
        apply_style(ws[address], spec["style"])

    # Recreate original merged cells.
    for merged in data["merged_cells"]:
        ws.merge_cells(merged)

    # Transfer static labels only; never transfer historical measurements.
    # Keep references to the current cover sheet where appropriate.
    cover_links = {
        "K6": "='Cover generic'!C7",
        "K7": "='Cover generic'!J9",
        "K8": "='Cover generic'!J10",
        "K9": "='Cover generic'!J14",
        "K10": "='Cover generic'!J13",
        "K11": "='Cover generic'!C12",
        "K12": '=CONCATENATE(\'Cover generic\'!D19,"; ",\'Cover generic\'!D20)',
        "C95": "='Cover generic'!B24",
    }

    for address, spec in data["cells"].items():
        value = spec["value"]
        if value is None:
            continue
        cell = ws[address]
        if cell.__class__.__name__ == "MergedCell":
            continue
        if address in cover_links:
            cell.value = cover_links[address]
        elif isinstance(value, str) and value.startswith("="):
            # Skip historical formulas, including RAD MODE references.
            continue
        elif isinstance(value, (int, float)):
            # Do not import historical numeric measurements.
            continue
        elif isinstance(value, str):
            cell.value = value

    # Match the original Illinois State Form print configuration.
    from openpyxl.worksheet.pagebreak import Break
    from openpyxl.worksheet.page import PageMargins

    ws.print_area = "B1:Q107"

    ws.sheet_properties.pageSetUpPr.fitToPage = False
    ws.page_setup.orientation = "portrait"
    ws.page_setup.scale = 70
    ws.page_setup.fitToWidth = None
    ws.page_setup.fitToHeight = None

    ws.page_margins = PageMargins(
        left=0.7,
        right=0.7,
        top=0.75,
        bottom=0.75,
        header=0.3,
        footer=0.3,
    )

    ws.row_breaks.brk = []
    ws.row_breaks.append(Break(id=64))

    ws.sheet_view.view = "pageBreakPreview"
    ws.sheet_view.zoomScale = 143


def populate_state_form_equipment(ws, report):
    """Populate State Form equipment details from report information."""

    from datetime import date
    from openpyxl.styles import Alignment

    def value(key):
        v = report.get(key)
        return str(v).strip() if v is not None else ""

    def location():
        parts = [
            value("site"),
            value("building"),
            value("room"),
        ]
        return ", ".join(p for p in parts if p)

    # Page 1: equipment information
    fields = {
        "K4": value("facility_name"),
        "K5": value("facility_id"),
        "K7": value("manufacturer"),
        "K8": value("model"),
        "K9": value("ceid"),
        "K10": value("iema_number"),
        "K11": value("building"),
        "O9": value("year_of_manufacture"),
    }

    for address, text in fields.items():
        if text:
            ws[address] = text
        elif address != "K4":
            ws[address] = None

    # Preserve the institution name when facility_name is blank.
    if not value("facility_name"):
        ws["K4"] = "University of Chicago Hospital"

    # Survey date
    raw_date = value("inspection_date")
    if raw_date:
        try:
            ws["K6"] = date.fromisoformat(raw_date)
            ws["K6"].number_format = "mmmm d, yyyy"
        except ValueError:
            ws["K6"] = raw_date
    else:
        ws["K6"] = None

    # Inspector information
    people = [
        value("medical_physicist"),
        value("trainee"),
    ]
    credentials = {
        "Cameron Kofler": "C. Kofler, PhD, DABR",
        "Benjamin Heggie": "B. Heggie, PhD",
        "Muhammad Imran": "M. Imran, PhD",
    }

    formatted_people = []
    for entry in people:
        for name in entry.split(","):
            name = name.strip()
            if name:
                formatted_people.append(credentials.get(name, name))

    ws["K12"] = "; ".join(formatted_people)

    # STATE FORM HEADER EXTENSION

    # Inspector ID selected in the report form.
    ws["Q13"] = value("inspector_id") or None

    # Selected test equipment and its calibration dates.
    models = [
        x.strip() for x in value("test_equipment").split(";") if x.strip()
    ]
    serials = [
        x.strip() for x in value("test_equipment_serial").split(";") if x.strip()
    ]
    dates = [
        x.strip() for x in value("calibration_date").split(";") if x.strip()
    ]

    equipment_lines = []
    for i, serial in enumerate(serials):
        model = models[i] if i < len(models) else "Radcal AG Touchpro w/AGDM+"
        calibration = dates[i] if i < len(dates) else ""

        if calibration:
            try:
                calibration = date.fromisoformat(calibration).strftime("%m/%d/%Y")
            except ValueError:
                pass

        text = f"{model}; S/N: {serial}"
        if calibration:
            text += f"; CALIBRATION DATE: {calibration}"

        equipment_lines.append(text)

    ws["C3"] = "; ".join(equipment_lines) if equipment_lines else None

    # Page 2: reference Page 1 rather than duplicate values.
    references = {
        "K68": "K6",
        "K69": "K7",
        "K70": "K8",
        "K71": "K9",
        "K72": "K10",
        "K73": "K11",
    }

    for destination, source in references.items():
        ws[destination] = f'=IF({source}="","",{source})'

    ws["K68"].number_format = "mmmm d, yyyy"


def populate_state_form_reproducibility(ws, qc_data):
    """Populate State Form exposure reproducibility measurements."""

    measurements = qc_data.get(
        "radiography_qc", {}
    ).get("values", {})

    results = qc_data.get(
        "qc_results", {}
    ).get("values", {})

    reproducibility = results.get("reproducibility", {})

    # First mAs setting
    mas = measurements.get("mas4")
    ws["K19"] = mas if isinstance(mas, (int, float)) and mas > 0 else None

    # Four repeated exposure measurements
    for index, column in enumerate("LMNO", start=1):
        value = measurements.get(f"rep_exp{index}")
        ws[f"{column}19"] = (
            value
            if isinstance(value, (int, float)) and value > 0
            else None
        )

    # Coefficient of variation
    cv = reproducibility.get("cv")

    ws["P19"] = (
        cv
        if isinstance(cv, (int, float))
        else None
    )

    # Mean output per mAs
    mean = reproducibility.get("mean")

    if (
        isinstance(mean, (int, float))
        and isinstance(mas, (int, float))
        and mas > 0
    ):
        ws["Q19"] = mean / mas
    else:
        ws["Q19"] = None

    # Overall coefficient of linearity
    # Additional exposures at 25 mAs
    import statistics

    for cell, key in (
        ("M21", "s3_exp2"),
        ("N21", "s3_exp3"),
        ("O21", "s3_exp4"),
    ):
        value = measurements.get(key)
        ws[cell] = value if isinstance(value, (int, float)) and value > 0 else None

    exposures = [ws[f"{col}21"].value for col in "LMNO"]

    if all(isinstance(v, (int, float)) and v > 0 for v in exposures):
        ws["P21"] = (
            statistics.pstdev(exposures) / statistics.mean(exposures)
        )
    else:
        ws["P21"] = None

    linearity = results.get("linearity", {})
    coefficient = linearity.get("maximum_linearity_coefficient")

    ws["Q23"] = (
        coefficient
        if isinstance(coefficient, (int, float))
        and math.isfinite(coefficient)
        and 0 <= coefficient <= 1
        else None
    )

    # Remaining linearity settings
    for row, mas_key, dose_key in [
        (20, "mas1", "dose1"),
        (21, "mas2", "dose2"),
        (22, "mas3", "dose3"),
    ]:
        mas_value = measurements.get(mas_key)
        dose_value = measurements.get(dose_key)

        valid_mas = (
            isinstance(mas_value, (int, float))
            and mas_value > 0
        )

        valid_dose = (
            isinstance(dose_value, (int, float))
            and dose_value > 0
        )

        ws[f"K{row}"] = mas_value if valid_mas else None
        ws[f"L{row}"] = dose_value if valid_dose else None

        ws[f"Q{row}"] = (
            dose_value / mas_value
            if valid_mas and valid_dose
            else None
        )



    # Final C.V. for the four 25 mAs measurements
    import statistics
    exposures = [ws[f"{c}21"].value for c in "LMNO"]

    if all(isinstance(v, (int, float)) and v > 0 for v in exposures):
        ws["P21"] = statistics.pstdev(exposures) / statistics.mean(exposures)
    else:
        ws["P21"] = None

def populate_state_form_techniques(ws, qc_data):
    """Populate available State Form technique settings."""
    import math

    measurements = qc_data.get("radiography_qc", {}).get("values", {})
    ese = qc_data.get("entrance_skin_exposure", {}).get("values", {})

    def valid(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    # Source-to-detector distance for reproducibility / linearity
    ws["Q15"] = 100

    # Reproducibility / linearity technique settings.
    # The original State Form references RAD MODE D60 (0.1 seconds).
    exposure_time_seconds = 0.1

    for row in range(19, 23):
        ws[f"J{row}"] = exposure_time_seconds
        mas = ws[f"K{row}"].value
        ws[f"I{row}"] = (
            mas / exposure_time_seconds if valid(mas) else None
        )

    # Nominal kVp used for reproducibility and linearity testing.
    nominal = measurements.get("linearity_kvp_nominal")
    ws["N15"] = nominal if valid(nominal) else None

    # Beam Quality: technique from available QC data.
    ws["O27"] = nominal if valid(nominal) else None

    beam_mas = ese.get("entrance_exposure_mas_80")
    if beam_mas is None:
        beam_mas = ese.get("ese_mas_80")

    ws["O28"] = beam_mas if valid(beam_mas) else None

    # Original State Form specifies 100 ms.
    ws["O29"] = 100


def populate_state_form_ese_table(ws):
    """Restore ESE table references and reference settings."""

    thicknesses = [23, 23, 23, 23, 13, 15, 8]
    sid_cm = [183, 183, 101.6, 101.6, 101.6, 101.6, 101.6]
    limits = [35, 30, 600, 800, 200, 250, 100]

    for index, row in enumerate(range(81, 88)):
        rad_row = 244 + index

        ws[f"G{row}"] = thicknesses[index]
        ws[f"H{row}"] = f"=G{row}/2.54"

        ws[f"I{row}"] = f"='RAD MODE'!F{rad_row}"
        ws[f"J{row}"] = f"='RAD MODE'!G{rad_row}"

        ws[f"L{row}"] = sid_cm[index]
        ws[f"M{row}"] = 72 if index < 2 else 40

        ws[f"N{row}"] = f"='RAD MODE'!J{rad_row}"
        ws[f"P{row}"] = limits[index]
        ws[f"Q{row}"] = f"='RAD MODE'!L{rad_row}"

def populate_state_form_hvl(ws, qc_data):
    import math

    hvl = qc_data.get("hvl", {}).get("values", {})
    measured = hvl.get("hvl_80")

    valid = (
        isinstance(measured, (int, float))
        and not isinstance(measured, bool)
        and math.isfinite(measured)
        and measured > 0
    )

    ws["Q30"] = measured if valid else None
    ws["Q31"] = None  # Pass/Fail calculated separately

def populate_state_form_kvp_accuracy(ws, qc_data):
    """Populate State Form kVp measurements directly from QC data."""
    import math

    values = qc_data.get("radiography_qc", {}).get("values", {})
    kvp_data = qc_data.get("kvp_accuracy", {}).get("values", {})

    def valid(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    # Selected kVp values
    for cell, nominal in (
        ("J28", 50),
        ("K28", 80),
        ("L28", 120),
    ):
        ws[cell] = nominal

    # State Form kVp mAs settings
    for row, key in (
        (30, "mas4"),
        (31, "mas1"),
        (32, "mas2"),
        (33, "mas3"),
    ):
        mas = values.get(key)
        ws[f"I{row}"] = mas if valid(mas) else None

    # Four measured kVp values from RAD MODE linearity testing
    readings = [
        values.get("linearity_kvp_1"),
        values.get("linearity_kvp_2"),
        values.get("linearity_kvp_3"),
        values.get("linearity_kvp_4"),
    ]

    for row, reading in zip(range(30, 34), readings):
        ws[f"K{row}"] = reading if valid(reading) else None

    # Average of available measurements
    valid_readings = [v for v in readings if valid(v)]
    ws["K34"] = (
        sum(valid_readings) / len(valid_readings)
        if valid_readings else None
    )

    # Preserve other measurement columns from existing RAD MODE references
    ws["J32"] = "='RAD MODE'!C90"
    ws["L32"] = "='RAD MODE'!C97"

    # Existing kVp accuracy assessment
    measured = [
        kvp_data.get(f"kvp_{nominal}")
        for nominal in (50, 60, 70, 80, 90, 100, 110, 120)
    ]

    if all(valid(v) for v in measured):
        errors = [
            abs(nominal - actual) / actual * 100
            for nominal, actual in zip(
                (50, 60, 70, 80, 90, 100, 110, 120),
                measured,
            )
        ]
        result = "PASS" if max(errors) < 10 else "FAIL"
    else:
        result = None

    for cell in ("J35", "K35", "L35"):
        ws[cell] = result


def populate_state_form_master_safety(ws, rad_ws, qc_data):
    """Write State Form safety results directly, without sheet links."""
    values = qc_data.get("equipment_safety", {}).get("values", {})

    # State Form column A = compliant or N/A;
    # column B = non-compliant.
    manual = {
        18: "deadman_switch",
        19: "preset_timer",
        20: "timer_accuracy",
        21: "zero_setting",
        24: "tube_stability",
        25: "tube_leakage",
        26: "standby_leakage",
        28: "technique_indicated",
        32: "aec_mode",
        33: "aec_reproducibility",
        34: "aec_mode",
        35: "aec_backup",
        38: "patient_communication",
        39: "beam_indicator",
        40: "protective_apparel",
        41: "technique_guides",
        43: "operator_shielding",
        44: "switch_shielding",
        45: "mobile_cord",
        46: "room_shielding",
        47: "gonadal_shielding",
        49: "collimator",
    }

    # Use actual QC results where the form describes measured tests.
    measured = {
        23: ("G114",),
        29: ("D75", "D105"),
        30: ("D73",),
        31: ("H59",),
        36: ("K228",),
        50: ("K116",),
        51: ("K143",),
        52: ("K208",),
    }

    def put_result(row, status):
        ws[f"A{row}"] = None
        ws[f"B{row}"] = None
        if status == "pass":
            ws[f"A{row}"] = "X"
        elif status == "fail":
            ws[f"B{row}"] = "X"
        elif status == "na":
            ws[f"A{row}"] = "N/A"

    for row, key in manual.items():
        entry = values.get(key, {})
        raw = str(entry.get("status", "Not assessed")).strip().lower()
        if raw == "compliant":
            status = "pass"
        elif raw == "non-compliant":
            status = "fail"
        elif raw in ("not applicable", "n/a", "na"):
            status = "na"
        else:
            status = None
        put_result(row, status)

    for row, addresses in measured.items():
        statuses = [
            str(rad_ws[address].value or "").strip().lower()
            for address in addresses
        ]
        if any(x in ("fail", "failed") for x in statuses):
            status = "fail"
        elif all(x == "pass" for x in statuses):
            status = "pass"
        else:
            status = None
        put_result(row, status)

    # Patient visibility and communication are separate RAD MODE checks.
    # State Form requires both for its combined communication item.
    combined = [
        str(values.get(key, {}).get("status", "")).strip().lower()
        for key in ("patient_visibility", "patient_communication")
    ]
    if any(x == "non-compliant" for x in combined):
        put_result(38, "fail")
    elif all(x == "compliant" for x in combined):
        put_result(38, "pass")
    elif all(x in ("compliant", "not applicable") for x in combined):
        put_result(38, "na")
    else:
        put_result(38, None)

    # Equipment-specific applicability from the reference State Form.
    # These are not measured compliance results.
    for row in (19, 20, 21, 26, 32, 33, 34, 35):
        ws[f"A{row}"] = "N/A"
        ws[f"B{row}"] = None

    for row in (25, 46):
        ws[f"A{row}"] = "on install"
        ws[f"B{row}"] = None

    # Directly transfer relevant measured status values.
    ws["Q31"] = rad_ws["G114"].value
