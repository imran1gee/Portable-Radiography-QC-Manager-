import math
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


def build_rad_mode(ws, qc_data):
    ws.sheet_view.showGridLines = False

    ws["B84"] = "kVp Accuracy and Tube Output"
    ws["B84"].font = Font(
        name="Arial", size=12, bold=True
    )

    headers = {
        "B88": "kVp Setting",
        "C88": "kVp Measured",
        "D88": "kVp Error (kV)",
        "E88": "kVp rel. Error (%)",
        "F88": "mAs",
        "G88": "Exposure",
        "H88": "Factor to 100cm",
        "I88": "Output",
        "J88": "HVL (mm Al)",
        "G89": "(mR)",
        "I89": "(mR/mAs)",
    }

    for address, value in headers.items():
        ws[address] = value

    kvp = qc_data.get("kvp_accuracy", {}).get("values", {})
    ese = qc_data.get(
        "entrance_skin_exposure", {}
    ).get("values", {})
    hvl = qc_data.get("hvl", {}).get("values", {})

    distance = ese.get("ese_measurement_distance_in")

    valid_distance = (
        isinstance(distance, (int, float))
        and not isinstance(distance, bool)
        and math.isfinite(distance)
        and distance > 0
    )

    ws["B86"] = "SID (in)"
    ws["C86"] = distance if valid_distance else None

    def valid_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    for row, nominal in enumerate(
        range(50, 121, 10), start=90
    ):
        measured = kvp.get(f"kvp_{nominal}")
        mas = ese.get(f"ese_mas_{nominal}")
        exposure = ese.get(f"ese_exposure_{nominal}")

        ws[f"B{row}"] = nominal

        if valid_number(measured):
            ws[f"C{row}"] = measured
            ws[f"D{row}"] = f"=B{row}-C{row}"
            ws[f"E{row}"] = (
                f"=ABS(D{row}/C{row})"
            )
            ws[f"E{row}"].number_format = "0.00%"

        if valid_number(mas):
            ws[f"F{row}"] = mas

        if valid_number(exposure):
            ws[f"G{row}"] = exposure

        if valid_distance:
            ws[f"H{row}"] = (
                f"=($C$86*2.54/100)^2"
            )

        if (
            valid_number(mas)
            and valid_number(exposure)
            and valid_distance
        ):
            ws[f"I{row}"] = (
                f"=H{row}*G{row}/F{row}"
            )

        value = hvl.get(f"hvl_{nominal}")
        ws[f"J{row}"] = value if valid_number(value) else None



def populate_rad_mode_summary(ws, qc_data):
    import math

    kvp = qc_data.get("kvp_accuracy", {}).get("values", {})
    hvl = qc_data.get("hvl", {}).get("values", {})

    nominal_values = range(50, 121, 10)
    errors = []

    for nominal in nominal_values:
        measured = kvp.get(f"kvp_{nominal}")

        if (
            not isinstance(measured, (int, float))
            or isinstance(measured, bool)
            or not math.isfinite(measured)
            or measured <= 0
        ):
            errors = []
            break

        errors.append(abs(nominal - measured) / measured)

    ws["B105"] = "Max kVp error"
    ws["C105"] = max(errors) if len(errors) == 8 else None
    ws["C105"].number_format = "0.00%"

    ws["D105"] = (
        "Pass" if max(errors) < 0.10 else "FAIL"
    ) if len(errors) == 8 else None

    ws["D113"] = "kVp"
    ws["E113"] = 80

    ws["D114"] = "HVL"
    ws["F114"] = "mm Al"

    measured_hvl = hvl.get("hvl_80")

    valid_hvl = (
        isinstance(measured_hvl, (int, float))
        and not isinstance(measured_hvl, bool)
        and math.isfinite(measured_hvl)
        and measured_hvl > 0
    )

    ws["E114"] = measured_hvl if valid_hvl else None

    ws["G114"] = (
        "Pass" if measured_hvl > 2.9 else "FAIL"
    ) if valid_hvl else None


def apply_original_rad_mode_layout(ws):
    """
    Rebuild RAD MODE formatting from extracted JSON.
    Does not copy historical measurement values or formulas.
    """
    import json
    from pathlib import Path
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Color
    from openpyxl.utils.cell import coordinate_from_string

    path = Path(__file__).parent / "layouts" / "rad_mode.json"
    data = json.loads(path.read_text())

    def make_color(spec):
        if not spec or not isinstance(spec, dict):
            return None
        kind = spec.get("type")
        if kind == "rgb" and spec.get("rgb"):
            return Color(rgb=spec["rgb"])
        if kind == "indexed" and spec.get("indexed") is not None:
            return Color(indexed=spec["indexed"])
        if kind == "theme" and spec.get("theme") is not None:
            return Color(
                theme=spec["theme"],
                tint=spec.get("tint") or 0
            )
        return None

    def make_side(spec):
        if not spec:
            return Side()
        return Side(
            style=spec.get("style"),
            color=make_color(spec.get("color"))
        )

    ws.sheet_view.showGridLines = False

    for col, spec in data["columns"].items():
        ws.column_dimensions[col].width = spec.get("width") or 8.43
        ws.column_dimensions[col].hidden = spec.get("hidden", False)

    for row, spec in data["rows"].items():
        if spec.get("height") is not None:
            ws.row_dimensions[int(row)].height = spec["height"]
        ws.row_dimensions[int(row)].hidden = spec.get("hidden", False)

    for address, entry in data["cells"].items():
        cell = ws[address]
        style = entry.get("style", {})

        font = style.get("font", {})
        cell.font = Font(
            name=font.get("name") or "Arial",
            size=font.get("size") or 10,
            bold=font.get("bold"),
            italic=font.get("italic"),
            underline=font.get("underline"),
            color=make_color(font.get("color")),
        )

        fill = style.get("fill", {})
        cell.fill = PatternFill(
            patternType=fill.get("patternType"),
            fgColor=make_color(fill.get("fgColor")) or Color(rgb="00000000"),
        )

        align = style.get("alignment", {})
        cell.alignment = Alignment(
            horizontal=align.get("horizontal"),
            vertical=align.get("vertical"),
            wrap_text=align.get("wrap_text"),
            text_rotation=align.get("text_rotation") or 0,
        )

        border = style.get("border", {})
        cell.border = Border(
            left=make_side(border.get("left")),
            right=make_side(border.get("right")),
            top=make_side(border.get("top")),
            bottom=make_side(border.get("bottom")),
        )

        cell.number_format = style.get("number_format") or "General"

        # Retain only static text, not historical results.
        value = entry.get("value")
        if isinstance(value, str) and not value.startswith("="):
            cell.value = value

    for merged_range in data.get("merged_cells", []):
        ws.merge_cells(merged_range)

    settings = data.get("print_options", {})
    ws.page_setup.orientation = settings.get("orientation")
    ws.page_setup.paperSize = settings.get("paper_size")
    ws.page_setup.fitToWidth = settings.get("fit_to_width")
    ws.page_setup.fitToHeight = settings.get("fit_to_height")
    ws.page_setup.scale = settings.get("scale")

    if data.get("print_area"):
        ws.print_area = data["print_area"]


def clean_rad_mode_historical_data(ws):
    """
    Remove historical data from the reconstructed RAD MODE sheet.
    Preserve formatting, headings, and static instructions.
    """
    import re

    # Historical equipment and personnel information.
    for address in (
        "K6", "M6", "N6", "M7", "N7",
        "F8", "M8", "N8", "H9",
        "M10", "M11",
    ):
        ws[address] = None

    # Clear historical safety checklist responses.
    for row in range(27, 52):
        for col in ("I", "J"):
            value = ws[f"{col}{row}"].value
            if isinstance(value, str) and value.strip().upper() in (
                "X", "NA", "N/A", "YES", "NO"
            ):
                ws[f"{col}{row}"] = None

    # Remove historical status results throughout RAD MODE.
    # This does not remove labels containing explanatory text.
    for row in ws:
        for cell in row:
            value = cell.value
            if isinstance(value, str) and value.strip().upper() in (
                "PASS", "FAIL", "FAILED"
            ):
                cell.value = None

    # Clear historical numeric constants outside the active
    # measurement table. Existing current calculations are added
    # afterward by build_rad_mode().
    for row in ws:
        for cell in row:
            if isinstance(cell.value, (int, float)) and not isinstance(
                cell.value, bool
            ):
                cell.value = None


def populate_rad_mode_header(ws, info):
    """Populate RAD MODE header from current report information."""
    from datetime import date, datetime

    def value(key):
        item = info.get(key)
        if item is None:
            return None
        text = str(item).strip()
        return text if text else None

    def put(address, key):
        ws[address] = value(key)

    # Current report information
    put("J4", "report_number")
    put("C5", "building")
    put("G5", "room")
    put("J5", "inspection_date")
    put("C6", "medical_physicist")
    put("C7", "manufacturer")
    put("F7", "model")
    put("B8", "ceid")
    put("F8", "serial_number")
    put("K8", "year_of_manufacture")
    put("C9", "equipment_type")
    put("K9", "iema_number")

    # Inspector ID selected in the Streamlit report form.
    put("K6", "inspector_id")

    # RAD MODE ADDITIONAL HEADER FIELDS
    from openpyxl.cell.cell import MergedCell

    def safe_put(address, item):
        cell = ws[address]
        if not isinstance(cell, MergedCell):
            cell.value = item

    # Generator type.
    safe_put("G9", value("generator_type"))

    # Test equipment selected in the Streamlit application.
    equipment = value("test_equipment")
    serials = value("test_equipment_serial")
    dates = value("calibration_date")

    equipment_list = equipment.split("; ") if equipment else []
    serial_list = serials.split("; ") if serials else []
    date_list = dates.split("; ") if dates else []

    for index, address in enumerate(("M10", "M11")):
        if index < len(serial_list):
            model = (
                equipment_list[index]
                if index < len(equipment_list)
                else "Radcal AG Touchpro w/AGDM+"
            )
            serial = serial_list[index]
            calibration = (
                date_list[index]
                if index < len(date_list)
                else ""
            )

            text = f"{model}; S/N: {serial}"
            if calibration:
                text += f"; CALIBRATION DATE: {calibration}"

            safe_put(address, text)
        else:
            safe_put(address, None)

    # Trainees are included alongside the medical physicist.
    physicist = value("medical_physicist")
    trainees = value("trainee")

    names = [name for name in (physicist, trainees) if name]
    ws["C6"] = ", ".join(names) if names else None


def populate_rad_mode_reproducibility_linearity(ws, qc_data):
    """Populate RAD MODE reproducibility and linearity from saved QC data."""
    import math
    import statistics

    values = qc_data.get("radiography_qc", {}).get("values", {})

    def valid_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    # Reproducibility: four repeated exposure measurements.
    exposures = [values.get(f"rep_exp{i}") for i in range(1, 5)]

    for row, exposure in enumerate(exposures, start=66):
        ws[f"C{row}"] = exposure if valid_number(exposure) else None

    if all(valid_number(x) for x in exposures):
        mean = statistics.mean(exposures)
        cv = statistics.stdev(exposures) / mean

        ws["C70"] = mean
        ws["C71"] = cv
        ws["E59"] = cv
        ws["H59"] = "Pass" if cv < 0.05 else "FAIL"
    else:
        for address in ("C70", "C71", "E59", "H59"):
            ws[address] = None

    # Linearity: three mAs / exposure measurements.
    measurements = [
        (values.get("mas1"), values.get("dose1"), "F62", "E66"),
        (values.get("mas2"), values.get("dose2"), "H62", "G66"),
        (values.get("mas3"), values.get("dose3"), "J62", "I66"),
    ]

    normalized = []

    for mas, dose, mas_cell, dose_cell in measurements:
        ws[mas_cell] = mas if valid_number(mas) else None
        ws[dose_cell] = dose if valid_number(dose) else None

        if valid_number(mas) and valid_number(dose):
            normalized.append(dose / mas)

    if len(normalized) == 3:
        maximum = max(normalized)
        minimum = min(normalized)
        coefficient = (maximum - minimum) / (maximum + minimum)

        ws["C73"] = coefficient
        ws["D73"] = "Pass" if coefficient < 0.1 else "FAIL"
    else:
        ws["C73"] = None
        ws["D73"] = None

    # The remaining kVp and combined results require separate data.
    for address in ("C75", "D75", "E75", "K53"):
        ws[address] = None


def populate_rad_mode_four_setting_linearity(ws, qc_data):
    """Populate four-setting linearity using current saved measurements."""
    import math
    import statistics

    values = qc_data.get("radiography_qc", {}).get("values", {})

    def valid(x):
        return (
            isinstance(x, (int, float))
            and not isinstance(x, bool)
            and math.isfinite(x)
            and x > 0
        )

    repeats = [values.get(f"rep_exp{i}") for i in range(1, 5)]
    mean = statistics.mean(repeats) if all(map(valid, repeats)) else None

    settings = [
        (values.get("mas4"), mean, "D62", "C70", "C72"),
        (values.get("mas1"), values.get("dose1"), "F62", "E70", "E72"),
        (values.get("mas2"), values.get("dose2"), "H62", "G70", "G72"),
        (values.get("mas3"), values.get("dose3"), "J62", "I70", "I72"),
    ]

    outputs = []

    for mas, exposure, mas_cell, mean_cell, output_cell in settings:
        ws[mas_cell] = mas if valid(mas) else None
        ws[mean_cell] = exposure if valid(exposure) else None

        output = exposure / mas if valid(mas) and valid(exposure) else None
        ws[output_cell] = output

        if output is not None:
            outputs.append(output)

    if len(outputs) == 4:
        coefficient = (
            (max(outputs) - min(outputs))
            / (max(outputs) + min(outputs))
        )
        ws["C73"] = coefficient
        ws["D73"] = "Pass" if coefficient < 0.1 else "FAIL"
    else:
        ws["C73"] = None
        ws["D73"] = None




def populate_rad_mode_test1_details(ws, qc_data):
    """Transfer saved Test 1 focal spots and exposure times."""
    import math

    values = qc_data.get("radiography_qc", {}).get("values", {})

    def number(key):
        value = values.get(key)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        ):
            return value
        return None

    # Existing exposure calculations are handled elsewhere.
    # Populate focal spots, first-trial exposures, and times.
    for setting, fs_col, time_col in (
        (1, "C", "D"),
        (2, "E", "F"),
        (3, "G", "H"),
        (4, "I", "J"),
    ):
        focal_spot = str(values.get(f"s{setting}_fs") or "").strip()
        ws[f"{fs_col}62"] = focal_spot or None

        if setting > 1:
            ws[f"{fs_col}66"] = number(f"dose{setting - 1}")

        for trial in range(1, 5):
            row = 65 + trial

            # Settings 2 and 4 have merged trial cells.
            if setting in (2, 4) and trial > 1:
                continue

            if setting == 3 and trial > 1:
                ws[f"G{row}"] = number(f"s3_exp{trial}")

            ws[f"{time_col}{row}"] = number(
                f"s{setting}_time{trial}"
            )


def populate_rad_mode_reproducibility(ws, qc_data):
    """Populate repeated exposures, mean, CV, and reproducibility result."""
    import math
    import statistics

    values = qc_data.get("radiography_qc", {}).get("values", {})
    exposures = [values.get(f"rep_exp{i}") for i in range(1, 5)]

    def valid(x):
        return (
            isinstance(x, (int, float))
            and not isinstance(x, bool)
            and math.isfinite(x)
            and x > 0
        )

    for row, exposure in enumerate(exposures, start=66):
        ws[f"C{row}"] = exposure if valid(exposure) else None

    if all(valid(x) for x in exposures):
        mean = statistics.mean(exposures)
        cv = statistics.stdev(exposures) / mean

        ws["C70"] = mean
        ws["C71"] = cv
        ws["E59"] = cv
        ws["H59"] = "Pass" if cv <= 0.05 else "FAIL"
    else:
        for address in ("C70", "C71", "E59", "H59"):
            ws[address] = None


def populate_rad_mode_overall_summary(ws):
    """Populate validated summary results without assuming missing tests passed."""

    # Historical equipment maintenance note.
    ws["G84"] = None

    def status(address):
        value = ws[address].value
        if not isinstance(value, str):
            return None

        result = value.strip().upper()
        return result if result in ("PASS", "FAIL") else None

    reproducibility = status("H59")
    linearity = status("D73")
    kvp = status("D105")
    hvl = status("G114")

    # Original combined assessment requires all three test results.
    four_setting_kvp = status("D75")

    if all((reproducibility, linearity, four_setting_kvp)):
        ws["K53"] = (
            "Pass"
            if all(x == "PASS" for x in
                   (reproducibility, linearity, four_setting_kvp))
            else "FAIL"
        )
    else:
        ws["K53"] = None

    # Output / kVp / HVL requires all three test results.
    output = status("D84")

    if output and kvp and hvl:
        ws["K77"] = (
            "Pass"
            if all(x == "PASS" for x in (output, kvp, hvl))
            else "FAIL"
        )
    else:
        ws["K77"] = None


def populate_rad_mode_four_setting_kvp(ws, qc_data):
    """Populate kVp accuracy for the four reproducibility/linearity settings."""
    import math

    values = qc_data.get("radiography_qc", {}).get("values", {})

    def valid(x):
        return (
            isinstance(x, (int, float))
            and not isinstance(x, bool)
            and math.isfinite(x)
            and x > 0
        )

    # Dedicated measurements, not the separate kVp accuracy test.
    nominal = values.get("linearity_kvp_nominal")
    readings = [
        values.get("linearity_kvp_1"),
        values.get("linearity_kvp_2"),
        values.get("linearity_kvp_3"),
        values.get("linearity_kvp_4"),
    ]

    ws["B60"] = nominal if valid(nominal) else None

    for address, reading in zip(("D63", "F63", "H63", "J63"), readings):
        ws[address] = reading if valid(reading) else None

    errors = []

    for address, reading in zip(("C74", "E74", "G74", "I74"), readings):
        if valid(nominal) and valid(reading):
            error = abs(reading - nominal)
            ws[address] = error
            errors.append(error / nominal)
        else:
            ws[address] = None

    if len(errors) == 4:
        maximum_error = max(errors)
        ws["C75"] = maximum_error * nominal
        ws["C75"].number_format = "0.00"

        ws["E75"] = maximum_error
        ws["E75"].number_format = "0.0%"

        ws["F75"] = "Pass" if maximum_error <= 0.05 else "FAIL"
    else:
        ws["C75"] = None
        ws["E75"] = None
        ws["F75"] = None



def restore_test1_result_formatting(ws):
    """Complete Test 1 CV and result formatting."""
    import math
    import statistics
    from openpyxl.styles import PatternFill

    yellow = PatternFill(
        fill_type="solid",
        fgColor="FFFFFF00"
    )
    red = PatternFill(
        fill_type="solid",
        fgColor="FFFFB8B8"
    )

    # Second CV: repeated exposures for setting 3.
    exposures = [
        ws[f"G{row}"].value
        for row in range(66, 70)
    ]

    if all(
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and math.isfinite(x)
        and x > 0
        for x in exposures
    ):
        mean = statistics.mean(exposures)
        cv = statistics.stdev(exposures) / mean
        ws["G71"] = cv
    else:
        ws["G71"] = None

    ws["G71"].number_format = "0.000"
    ws["G71"].fill = yellow

    # Maximum kVp error and assessment.
    ws["E75"].number_format = "0.0%"
    ws["E75"].fill = yellow

    result = str(ws["F75"].value or "").strip().lower()
    if result == "pass":
        ws["F75"].fill = yellow
    elif result == "fail":
        ws["F75"].fill = red

    # CV of exposure time for Settings 1 and 3.
    import statistics
    from services.qc_data import load_qc_data

    values = load_qc_data().get("radiography_qc", {}).get("values", {})

    for setting, cell in ((1, "D71"), (3, "H71")):
        times = [
            values.get(f"s{setting}_time{i}")
            for i in range(1, 5)
        ]

        if all(
            isinstance(t, (int, float))
            and not isinstance(t, bool)
            and t > 0
            for t in times
        ):
            ws[cell] = statistics.stdev(times) / statistics.mean(times)
        else:
            ws[cell] = None

        ws[cell].number_format = "0.000"

    # TEST1_FINAL_AVERAGES
    # Calculate averages from actual worksheet measurements.
    import statistics

    for column in ("D", "H"):
        measurements = [
            ws[f"{column}{row}"].value
            for row in range(66, 70)
        ]

        if all(
            isinstance(x, (int, float))
            and not isinstance(x, bool)
            and x > 0
            for x in measurements
        ):
            ws[f"{column}70"] = statistics.mean(measurements)
        else:
            ws[f"{column}70"] = None

        ws[f"{column}70"].number_format = "0.0"

    # Put the kVp Pass/FAIL result in D75.
    result = str(ws["F75"].value or "").strip()

    if result.upper() in ("PASS", "FAIL"):
        ws["D75"] = result
        ws["F75"] = None

def apply_rad_mode_precision_fix(ws):
    """Improve measurement display and remove historical field-size labels."""
    # RAD_MODE_PRECISION_FIX

    for row in range(66, 71):
        ws[f"C{row}"].number_format = "0.00"

    for address in ("C72", "E72", "G72", "I72"):
        ws[address].number_format = "0.000"

    ws["C73"].number_format = "0.0000"

    for address in ("C62", "E62", "G62", "I62"):
        ws[address] = None


def remove_rad_mode_historical_inspection_data(ws):
    """Clear historical inspection values without modifying merged cells."""
    from openpyxl.cell.cell import MergedCell

    historical_cells = [
        "H60", "I86", "G82",
        "B120", "B147", "B148", "B150",
        "E151", "I151",
        "B157", "B162",
        "K166", "K167", "D171",
        "B174", "D175", "D184",
        "B193",
    ]

    for address in historical_cells:
        cell = ws[address]
        if not isinstance(cell, MergedCell):
            cell.value = None

    for row in (177, 178, 181, 182, 186, 187, 190, 191):
        for col in ("B", "D", "E", "G", "H", "I", "J", "K"):
            cell = ws[f"{col}{row}"]
            if not isinstance(cell, MergedCell):
                cell.value = None




def populate_rad_mode_safety_checklist(ws, qc_data):
    """Populate original Excel safety checklist from assessed safety data."""
    from openpyxl.cell.cell import MergedCell

    mapping = {27: 'warning_label', 28: 'tube_stability', 29: 'technique_indicated', 30: 'beam_indicator', 31: 'door_interlocks', 32: 'patient_visibility', 33: 'patient_communication', 34: 'switch_shielding', 36: 'deadman_switch', 38: 'exposure_cables', 39: 'perpendicular_indicator', 41: 'minimum_field_size', 42: 'technique_guides', 43: 'gonadal_shielding', 44: 'protective_apparel', 46: 'cassette_cleaning', 47: 'cassette_condition', 50: 'mobile_operator_distance', 51: 'minimum_ssd'}
    values = qc_data.get("equipment_safety", {}).get("values", {})
    complete = True
    failed = False

    for row, key in mapping.items():
        status = values.get(key, {}).get("status", "Not assessed")
        status = str(status).strip().lower()

        for col in ("I", "J"):
            cell = ws[f"{col}{row}"]
            if not isinstance(cell, MergedCell):
                cell.value = None

        if status == "compliant":
            ws[f"I{row}"] = "X"
        elif status == "non-compliant":
            ws[f"J{row}"] = "X"
            failed = True
        elif status in ("n/a", "na", "not applicable"):
            ws[f"I{row}"] = "N/A"
        else:
            complete = False

    result = "FAIL" if failed else "Pass" if complete else None
    ws["K26"] = result
    ws["K13"] = result

def populate_rad_mode_test_summary(ws):
    """Populate QC test names and available results."""

    tests = [
        "SAFETY CHECK LIST",
        "EXPOSURE REPRODUCIBILITY and LINEARITY",
        "OUTPUT / KVP ACCURACY / HVL",
        "X-RAY / LIGHT FIELD ALIGNMENT",
        "LEGEND / NUMERICAL FIELD SIZE INDICATOR ACCURACY",
        "EXPOSURE INDEX (EI)",
        "X-RAY CENTRAL BEAM ALIGNMENT",
        "IMAGE QUALITY TESTS",
        "DAP ACCURACY",
        "SID ACCURACY",
        "LIGHT FIELD ILLUMINANCE",
        "ESE FORMULA AND SAMPLE ESE FOR PATIENTS",
    ]

    # Results must come from completed QC assessments.
    result_cells = [
        "K26",      # Safety checklist overall result
        "K53",      # Exposure reproducibility and linearity
        "K77",      # Output / kVp accuracy / HVL
        "K116",     # X-ray / light field alignment
        "K130",     # Numerical field size indicator
        "K153",     # Exposure index
        "K143",     # Central beam alignment
        "K173",     # Image quality
        "K196",     # DAP accuracy
        "K208",     # SID accuracy
        "K215",     # Light field illuminance
        "K228",     # ESE
    ]

    for row, (test, source) in enumerate(
        zip(tests, result_cells), start=13
    ):
        ws[f"B{row}"] = test

        result = ws[source].value if source else None

        if isinstance(result, str) and result.upper() in ("PASS", "FAIL"):
            ws[f"K{row}"] = result
        else:
            ws[f"K{row}"] = None


def populate_rad_mode_light_field_alignment(ws, qc_data):
    """Populate light-field alignment using original Excel cell mapping."""
    import math

    values = qc_data.get("light_field_alignment", {})
    if isinstance(values, dict) and isinstance(values.get("values"), dict):
        values = values["values"]

    keys = (
        "longitudinal_1",
        "longitudinal_2",
        "transverse_1",
        "transverse_2",
    )

    def valid(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    # Clear previous measurements and results.
    for address in (
        "F122", "F123",
        "C126", "D126", "E126", "F126",
        "D127", "F127", "G127",
        "C128", "E128", "K116", "K16",
    ):
        ws[address] = None

    sid = values.get("alignment_sid_cm")
    if not valid(sid) or sid <= 0:
        return

    ws["F122"] = sid / 2.54
    ws["F123"] = sid

    if not all(
        key in values and valid(values[key])
        for key in keys
    ):
        return

    for address, key in zip(
        ("C126", "D126", "E126", "F126"), keys
    ):
        ws[address] = values[key]
        ws[address].number_format = "0.00"

    sid_mm = sid * 10

    longitudinal = (
        abs(values["longitudinal_1"])
        + abs(values["longitudinal_2"])
    ) / sid_mm

    transverse = (
        abs(values["transverse_1"])
        + abs(values["transverse_2"])
    ) / sid_mm

    ws["D127"] = longitudinal
    ws["F127"] = transverse

    ws["D127"].number_format = "0.000%"
    ws["F127"].number_format = "0.000%"

    result = (
        "Pass"
        if longitudinal < 0.02 and transverse < 0.02
        else "FAIL"
    )

    ws["G127"] = result
    ws["K116"] = result
    ws["K16"] = result



def populate_rad_mode_ese(ws, qc_data):
    """Populate patient ESE using the same calculations as Streamlit."""
    import math
    from calculations.ese import (
        calculate_ese_regression,
        calculate_patient_ese,
    )

    values = qc_data.get("entrance_skin_exposure", {}).get("values", {})
    nominal_kvp = list(range(50, 121, 10))

    defaults = [
        (23, 120, 4, 183, 35),
        (23, 85, 2.8, 183, 30),
        (23, 75, 25, 100, 600),
        (23, 85, 25, 100, 800),
        (13, 75, 6.3, 100, 200),
        (15, 80, 6.3, 100, 250),
        (8, 65, 3.2, 100, 100),
    ]

    def number(key, default=None):
        try:
            value = float(values.get(key, default))
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    regression = None
    try:
        regression = calculate_ese_regression(
            kvp_values=nominal_kvp,
            exposures_mr=[
                number(f"ese_exposure_{k}") for k in nominal_kvp
            ],
            mas_values=[
                number(f"ese_mas_{k}") for k in nominal_kvp
            ],
            distance_in=number("ese_measurement_distance_in"),
        )
    except (ValueError, TypeError, OverflowError):
        pass

    ws["E237"] = regression["R"] if regression else None
    ws["E238"] = regression["X"] if regression else None

    dpr = number("ese_dpr_in", 0)
    ws["E240"] = dpr

    statuses = []

    for index, (pt0, kv0, ma0, sid0, limit0) in enumerate(defaults):
        row = 244 + index

        pt = number(f"ese_patient_thickness_{index}", pt0)
        kv = number(f"ese_patient_kvp_{index}", kv0)
        ma = number(f"ese_patient_mas_{index}", ma0)
        sid = number(f"ese_patient_sid_{index}", sid0)
        limit = number(f"ese_patient_limit_{index}", limit0)

        for col, value in (
            ("D", pt), ("F", kv), ("G", ma),
            ("H", sid), ("K", limit),
        ):
            ws[f"{col}{row}"] = value

        ws[f"E{row}"] = f"=D{row}/2.54" if pt is not None else None
        ws[f"I{row}"] = f"=H{row}/2.54" if sid is not None else None
        ws[f"J{row}"] = None
        ws[f"L{row}"] = None

        if regression is None or dpr is None:
            continue

        try:
            result = calculate_patient_ese(
                R=regression["R"],
                X=regression["X"],
                kvp=kv,
                mas=ma,
                sid_cm=sid,
                patient_thickness_cm=pt,
                dpr_in=dpr,
                ese_limit_mr=limit,
            )
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            continue

        ws[f"J{row}"] = result["ese_mr"]
        ws[f"L{row}"] = result["result"]
        statuses.append(result["result"])

    ws["K228"] = ws["K24"] = (
        "Pass" if len(statuses) == 7
        and all(s.upper() == "PASS" for s in statuses)
        else "FAIL" if len(statuses) == 7
        else None
    )


def populate_rad_mode_field_size(ws, qc_data):
    """Export numerical field size accuracy from saved QC measurements."""
    import math

    values = qc_data.get("field_size_accuracy", {}).get("values", {})

    def number(key, default=None):
        try:
            value = values.get(key, default)
            if value is None or isinstance(value, bool):
                return None
            value = float(value)
            return value if math.isfinite(value) and value > 0 else None
        except (TypeError, ValueError):
            return None

    measured_at = number("measurement_distance_in", 39.37)
    sid = number("indicated_sid_in", 39.37)

    ws["D134"] = measured_at
    ws["D135"] = sid

    statuses = []

    for index, size in enumerate((17.0, 12.0, 8.0), 1):
        row = 138 + index

        for dimension, selected_col, measured_col, error_col, status_col in (
            ("length", "B", "D", "F", "H"),
            ("width", "C", "E", "G", "I"),
        ):
            selected = number(f"selected_{dimension}_{index}", size)
            measured = number(f"measured_{dimension}_{index}")

            ws[f"{selected_col}{row}"] = selected
            ws[f"{measured_col}{row}"] = measured
            ws[f"{error_col}{row}"] = None
            ws[f"{status_col}{row}"] = None

            if None in (selected, measured, measured_at, sid):
                continue

            error = (measured - selected) / sid
            passed = abs(error) <= 0.02

            ws[f"{error_col}{row}"] = error
            ws[f"{error_col}{row}"].number_format = "0.00%"
            ws[f"{status_col}{row}"] = "Pass" if passed else "FAIL"
            statuses.append(passed)

    overall = (
        None if len(statuses) != 6
        else "Pass" if all(statuses) else "FAIL"
    )

    ws["J133"] = overall
    ws["K130"] = overall


def populate_rad_mode_central_beam(ws, qc_data):
    """Export central beam alignment using the Streamlit calculation."""
    import math
    from calculations.central_beam_alignment import (
        calculate_central_beam_alignment,
    )

    values = qc_data.get("central_beam_alignment", {}).get("values", {})

    def number(key):
        value = values.get(key)
        try:
            if value is None or isinstance(value, bool):
                return None
            value = float(value)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    sid = number("central_beam_sid_cm")
    displacement = number("central_beam_displacement_mm")
    visual = str(values.get("central_beam_visual_check") or "").strip().upper()

    ws["E151"] = displacement
    ws["I151"] = visual if visual in ("Y", "N") else None

    ws["J151"] = None
    ws["K143"] = None

    if sid is None or sid <= 0 or displacement is None:
        return

    if visual not in ("Y", "N"):
        return

    try:
        result = calculate_central_beam_alignment(
            sid_cm=sid,
            displacement_mm=displacement,
            visual_check=visual,
        )
    except (ValueError, TypeError, OverflowError):
        return

    ws["J151"] = result["result"]
    ws["K143"] = result["result"]


def populate_rad_mode_exposure_index(ws, qc_data):
    """Export Test 7 EI measurements and results to RAD MODE."""
    import math

    values = qc_data.get("exposure_index", {}).get("values", {})

    def number(key, default=None):
        value = values.get(key, default)
        try:
            if value is None or isinstance(value, bool):
                return None
            value = float(value)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    def positive(key, default=None):
        value = number(key, default)
        return value if value is not None and value > 0 else None

    def setting(key, default):
        return positive(key, default)

    # Detector identification.
    for detector, row in ((1, 160), (2, 161)):
        for col, suffix in (("E", "serial"), ("G", "ceid")):
            value = values.get(f"ei_detector_{detector}_{suffix}")
            ws[f"{col}{row}"] = (
                str(value).strip() if value is not None and str(value).strip()
                else None
            )

    # Initial reference dosimeter measurement.
    ws["C165"] = setting("ei_reference_kvp", 70)
    ws["D165"] = setting("ei_reference_mas", 20)

    hvl = positive("ei_hvl_mm_al")
    reference_exposure = positive("ei_reference_exposure_ur")

    ws["E165"] = hvl
    ws["F165"] = reference_exposure
    ws["G165"] = reference_exposure / 114 if reference_exposure is not None else None
    ws["H165"] = reference_exposure / 114 * 100 if reference_exposure is not None else None

    hvl_pass = None if hvl is None else 6.55 <= hvl <= 7.05
    ws["E170"] = (
        None if hvl_pass is None
        else "Pass" if hvl_pass else "FAIL"
    )

    detector_statuses = []

    for detector in (1, 2):
        detector_row = 165 + detector
        dosimeter_row = 167 + detector

        ws[f"C{detector_row}"] = setting(f"ei_detector_{detector}_kvp", 70)
        ws[f"D{detector_row}"] = setting(f"ei_detector_{detector}_mas", 2)

        ws[f"C{dosimeter_row}"] = setting(f"ei_dosimeter_{detector}_kvp", 70)
        ws[f"D{dosimeter_row}"] = setting(f"ei_dosimeter_{detector}_mas", 2)

        displayed = number(f"ei_displayed_{detector}")
        if displayed is not None and displayed < 0:
            displayed = None

        exposure = positive(f"ei_exposure_{detector}_ur")
        expected = exposure / 114 * 100 if exposure is not None else None

        ws[f"I{detector_row}"] = displayed
        ws[f"F{dosimeter_row}"] = exposure
        ws[f"G{dosimeter_row}"] = exposure / 114 if exposure is not None else None
        ws[f"H{dosimeter_row}"] = expected

        di = values.get(f"ei_detector_{detector}_di")
        ws[f"K{detector_row}"] = (
            str(di).strip() if di is not None and str(di).strip()
            else "N/A"
        )

        ws[f"J{detector_row}"] = None
        ws[f"L{detector_row}"] = None

        if displayed is None or expected is None:
            detector_statuses.append(None)
            continue

        difference = (displayed - expected) / expected
        passed = abs(difference) <= 0.20

        ws[f"J{detector_row}"] = difference
        ws[f"J{detector_row}"].number_format = '+0.0%;-0.0%;0.0%'
        ws[f"L{detector_row}"] = "Pass" if passed else "FAIL"
        detector_statuses.append(passed)

    # Artifacts assessment.
    artifacts = str(values.get("ei_artifacts_noted") or "").strip().lower()

    if artifacts == "no":
        ws["D171"] = "No"
        ws["E171"] = "Pass"
    elif artifacts == "yes":
        ws["D171"] = "Yes"
        ws["E171"] = "FAIL"
    else:
        ws["D171"] = None
        ws["E171"] = None

    # Overall result requires a complete measurement set.
    complete = (
        all(status is not None for status in detector_statuses)
        and hvl_pass is not None
        and artifacts in ("yes", "no")
    )

    if not complete:
        ws["K153"] = None
    elif all(detector_statuses) and hvl_pass and artifacts == "no":
        ws["K153"] = "Pass"
    else:
        ws["K153"] = "FAIL"


def populate_rad_mode_image_quality(ws, qc_data):
    """Populate Test 8 image-quality data from the current QC session."""
    import math

    values = qc_data.get("image_quality", {}).get("values", {})

    def text_value(key, default=None):
        value = values.get(key, default)
        return str(value).strip() if value is not None and str(value).strip() else None

    def numeric_value(key):
        value = values.get(key)
        try:
            if value is None or isinstance(value, bool):
                return None
            number = float(value)
            return number if math.isfinite(number) and number > 0 else None
        except (TypeError, ValueError):
            return None

    def observation(key):
        value = text_value(key)
        return value if value in ("Yes", "No", "N/A") else None

    for detector, serial_row, acquisition_rows, measurement_rows in (
        ("small", 175, {"lfs": 177, "sfs": 178},
         {"sfs": 181, "lfs": 182}),
        ("large", 184, {"lfs": 186, "sfs": 187},
         {"lfs": 190, "sfs": 191}),
    ):
        ws[f"D{serial_row}"] = text_value(f"iq_{detector}_serial")

        for spot in ("lfs", "sfs"):
            prefix = f"iq_{detector}_{spot}"
            row = acquisition_rows[spot]

            defaults = {
                "protocol": "ABDOMEN_AP",
                "bucky": "table",
                "grid": '40" focused',
                "sid": '40"',
                "kvp": "80",
                "mas": "14" if detector == "small" else "20",
                "prior_lp": "N/A",
            }

            for col, field in (
                ("B", "protocol"),
                ("D", "bucky"),
                ("E", "grid"),
                ("G", "sid"),
                ("I", "kvp"),
                ("J", "mas"),
                ("K", "prior_lp"),
            ):
                ws[f"{col}{row}"] = text_value(
                    f"{prefix}_{field}", defaults[field]
                )

            ws[f"H{row}"] = spot.upper()

            result_row = measurement_rows[spot]
            ws[f"B{result_row}"] = spot.upper()
            ws[f"C{result_row}"] = numeric_value(f"{prefix}_ei")
            ws[f"D{result_row}"] = numeric_value(f"{prefix}_lp_mm")
            ws[f"E{result_row}"] = text_value(f"{prefix}_lp_change")
            ws[f"F{result_row}"] = observation(f"{prefix}_wedge")
            ws[f"H{result_row}"] = observation(f"{prefix}_contrast")
            ws[f"J{result_row}"] = observation(f"{prefix}_artifacts")

    assessment = text_value("image_quality_assessment")
    ws["K173"] = assessment if assessment in ("Pass", "FAIL") else None

    # Replace historical comments with current-session comments.
    ws["B193"] = text_value("image_quality_comments")


def populate_rad_mode_dap_accuracy(ws, qc_data):
    """Export Test 9 DAP accuracy using the Streamlit calculation."""
    import math

    values = qc_data.get("dap_accuracy", {}).get("values", {})

    defaults = {
        "dap_width_in": 17.0,
        "dap_height_in": 17.0,
        "dap_sid_cm": 101.6,
        "dap_kvp": 70.0,
        "dap_mas": 2.0,
    }

    def positive(key):
        value = values.get(key, defaults.get(key))
        try:
            if value is None or isinstance(value, bool):
                return None
            value = float(value)
            return value if math.isfinite(value) and value > 0 else None
        except (TypeError, ValueError):
            return None

    width = positive("dap_width_in")
    height = positive("dap_height_in")
    sid = positive("dap_sid_cm")
    kvp = positive("dap_kvp")
    mas = positive("dap_mas")
    exposure = positive("dap_exposure_mr")
    displayed = positive("dap_displayed")

    for cell, value in {
        "D202": width,
        "D203": height,
        "E202": sid,
        "F202": kvp,
        "G202": mas,
        "H202": exposure,
        "I203": displayed,
    }.items():
        ws[cell] = value

    area = (
        width * height * 2.54 * 2.54
        if width is not None and height is not None
        else None
    )

    calculated = (
        exposure / 114.0 * area
        if exposure is not None and area is not None
        else None
    )

    ws["D204"] = area
    ws["I202"] = calculated

    complete = all(
        value is not None
        for value in (width, height, sid, kvp, mas, exposure, displayed)
    )

    if not complete or calculated is None or calculated <= 0:
        ws["I204"] = None
        ws["I205"] = None
        ws["K196"] = None
        return

    difference = (displayed - calculated) / calculated
    result = "Pass" if abs(difference) < 0.30 else "FAIL"

    ws["I204"] = difference
    ws["I204"].number_format = '+0.0%;-0.0%;0.0%'
    ws["I205"] = result
    ws["K196"] = result


def populate_rad_mode_light_field_illuminance(ws, qc_data):
    """Populate Test 11 illuminance measurements and compliance results."""
    import math

    section = qc_data.get("light_field_illuminance", {})
    values = section.get("values", section)

    def nonnegative(key):
        value = values.get(key)
        try:
            if value is None or isinstance(value, bool) or value == "":
                return None
            number = float(value)
            return number if math.isfinite(number) and number >= 0 else None
        except (TypeError, ValueError):
            return None

    measurements = {
        "D222": nonnegative("q1_lux"),
        "D223": nonnegative("q2_lux"),
        "D224": nonnegative("q3_lux"),
        "D225": nonnegative("q4_lux"),
        "D226": nonnegative("background_lux"),
    }

    for cell, value in measurements.items():
        ws[cell] = value

    ws["G226"] = None
    ws["H226"] = None
    ws["I226"] = None
    ws["K215"] = None

    quadrants = [
        measurements[cell]
        for cell in ("D222", "D223", "D224", "D225")
    ]
    background = measurements["D226"]

    if background is None or any(
        value is None or value <= 0 for value in quadrants
    ):
        return

    corrected = sum(quadrants) / 4.0 - background
    federal = "Pass" if corrected > 160 else "FAIL"
    state = "Pass" if corrected > 100 else "FAIL"

    ws["G226"] = corrected
    ws["H226"] = federal
    ws["I226"] = state
    ws["K215"] = state


def populate_rad_mode_sid_accuracy(ws, qc_data):
    """Populate Test 10 SID accuracy from saved measurements."""
    import math
    from calculations.sid_accuracy import calculate_sid_accuracy

    section = qc_data.get("sid_accuracy", {})
    values = section.get("values", section)

    def positive(key, default=None):
        value = values.get(key, default)
        try:
            if value is None or isinstance(value, bool) or value == "":
                return None
            number = float(value)
            return number if math.isfinite(number) and number > 0 else None
        except (TypeError, ValueError):
            return None

    indicator = values.get("sid_indicator_type", "System tape")
    indicator = str(indicator).strip() if indicator is not None else ""

    set_sid = positive("sid_set_cm", 100.0)
    measured_sid = positive("sid_measured_cm")

    ws["B213"] = indicator or None
    ws["D213"] = set_sid
    ws["F213"] = measured_sid

    ws["E213"] = 0.02 * set_sid if set_sid is not None else None
    ws["H213"] = None
    ws["J213"] = None
    ws["K208"] = None

    if not indicator or set_sid is None or measured_sid is None:
        return

    result = calculate_sid_accuracy(set_sid, measured_sid)

    ws["E213"] = result["tolerance_cm"]
    ws["H213"] = result["difference_percent"] / 100.0
    ws["H213"].number_format = "0.00%"
    ws["J213"] = result["result"]
    ws["K208"] = result["result"]


def populate_rad_mode_output_constancy(ws, qc_data):
    """Populate 80-kVp measured output, baseline, and 10% constancy result."""
    import math

    values = qc_data.get("entrance_skin_exposure", {}).get("values", {})

    def positive(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    exposure = values.get("ese_exposure_80")
    mas = values.get("ese_mas_80")
    distance_in = values.get("ese_measurement_distance_in")
    baseline = values.get("tube_output_baseline")
    baseline_year = str(values.get("tube_output_baseline_year", "") or "").strip()

    measured = None

    if all(positive(x) for x in (exposure, mas, distance_in)):
        distance_cm = distance_in * 2.54
        measured = exposure / mas * (distance_cm / 100.0) ** 2

    # Baseline year is saved as metadata; numeric output cells stay unchanged.
    if baseline_year and (not baseline_year.isdigit() or len(baseline_year) != 4):
        baseline_year = ""

    if baseline_year:
        ws["B83"] = f"Baseline output ({baseline_year}):"
    else:
        ws["B83"] = "Baseline output:"

    technique_mas = values.get("tube_output_technique_mas", 25.0)
    copper_mm = values.get("tube_output_copper_mm", 0.0)

    ws["G86"] = technique_mas
    ws["I86"] = copper_mm

    ws["G86"].number_format = "0.0"
    ws["I86"].number_format = "0.0"

    ws["D82"] = measured
    ws["D83"] = baseline if positive(baseline) else None

    if measured is not None and positive(baseline):
        change = abs(measured - baseline) / baseline
        ws["D84"] = "Pass" if change <= 0.10 else "FAIL"
    else:
        ws["D84"] = None

    for address in ("D82", "D83"):
        ws[address].number_format = "0.00"
