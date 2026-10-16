import json
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.worksheet.page import PageMargins

from services.app_paths import REPORT_INFO, REPORTS_DIR
DATA = REPORT_INFO
REPORTS = REPORTS_DIR

DARK = "222222"
GRAY = "E8E8E8"
BORDER = Side(style="thin", color="888888")


def write(ws, address, value, size=10, bold=False,
          horizontal="left", vertical="center"):
    cell = ws[address]
    cell.value = "" if value is None else str(value)
    cell.font = Font(
        name="Arial",
        size=size,
        bold=bold,
        color=DARK
    )
    cell.alignment = Alignment(
        horizontal=horizontal,
        vertical=vertical,
        wrap_text=True
    )
    return cell


def add_image(ws, data, anchor, max_width, max_height):
    if not data:
        return

    image = Image(BytesIO(data))
    ratio = min(
        max_width / image.width,
        max_height / image.height,
        1
    )
    image.width *= ratio
    image.height *= ratio
    ws.add_image(image, anchor)


def generate_excel_report(logo_bytes=None, signature_bytes=None):
    if not DATA.exists():
        raise FileNotFoundError("Save report information first.")

    info = json.loads(DATA.read_text())
    REPORTS.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Cover generic"

    # Original Excel column widths
    widths = {
        "A": 3.5,
        "B": 13.1640625,
        "C": 10.1640625,
        "D": 10.1640625,
        "E": 6.5,
        "F": 5.6640625,
        "G": 7.83203125,
        "H": 4.5,
        "I": 11.83203125,
        "J": 21.83203125,
    }

    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    for row in range(1, 28):
        ws.row_dimensions[row].height = 19

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18.75
    ws.row_dimensions[24].height = 136

    ws.sheet_view.showGridLines = False

    # HEADER: original positions
    write(
        ws, "B1",
        "University of Chicago Medicine",
        size=13, bold=True
    )
    write(
        ws, "B2",
        "Department of Radiology",
        size=11, bold=True
    )
    write(
        ws, "B3",
        "Annual QC summary report",
        size=10
    )

    # Give the original headings enough width
    ws.merge_cells("B1:F1")
    ws.merge_cells("B2:F2")
    ws.merge_cells("B3:F3")

    for cell in ("B1", "B2", "B3"):
        ws[cell].alignment = Alignment(
            vertical="center",
            wrap_text=False,
            shrink_to_fit=True
        )

    # Optional institutional logo
    add_image(ws, logo_bytes, "I2", 210, 90)

    # REPORT DETAILS: original rows 6-8
    write(ws, "B6", "Report:", bold=True)
    ws.merge_cells("C6:J6")
    write(ws, "C6", info.get("report_number", ""))

    write(ws, "B7", "Survey Date:", bold=True)
    ws.merge_cells("C7:F7")
    write(ws, "C7", info.get("inspection_date", ""))

    write(ws, "B8", "Report Date:", bold=True)
    ws.merge_cells("C8:F8")
    write(
        ws, "C8",
        info.get("report_date") or date.today().isoformat()
    )

    # FACILITY: original rows 10-16
    facility = [
        (10, "Site", "site"),
        (11, "Department", "department"),
        (12, "Building / Location", "building"),
        (13, "Room", "room"),
        (14, "Street", "street"),
        (15, "City", "city"),
        (16, "Facility ID", "facility_id"),
    ]

    for row, label, key in facility:
        write(ws, f"B{row}", label, size=9, bold=True)
        ws.merge_cells(
            start_row=row, start_column=3,
            end_row=row, end_column=6
        )
        write(ws, f"C{row}", info.get(key, ""), size=9)

    # EQUIPMENT: original rows 8-16
    equipment = [
        (8, "Equipment Type", "equipment_type"),
        (9, "Manufacturer", "manufacturer"),
        (10, "Model", "model"),
        (11, "S/N", "serial_number"),
        (12, "DOM", "year_of_manufacture"),
        (13, "IEMA", "iema_number"),
        (14, "CEID", "ceid"),
        (15, "Site ID", "site_id"),
        (16, "ACR", "acr_number"),
    ]

    for row, label, key in equipment:
        ws.merge_cells(
            start_row=row, start_column=8,
            end_row=row, end_column=9
        )
        write(ws, f"H{row}", label, size=9, bold=True)
        write(ws, f"J{row}", info.get(key, ""), size=9)

    # Personnel
    write(ws, "B19", "Medical Physicist:", bold=True)
    ws.merge_cells("D19:J19")
    write(ws, "D19", info.get("medical_physicist", ""))

    write(ws, "B20", "Trainee:", bold=True)
    ws.merge_cells("D20:J20")
    write(ws, "D20", info.get("trainee", ""))

    # Signature: optional authorized image
    add_image(ws, signature_bytes, "D21", 180, 36)

    # Comments: original location and height
    write(ws, "B23", "COMMENTS:", bold=True)

    ws.merge_cells("B24:J24")
    comment = write(
        ws, "B24",
        info.get("comments", ""),
        size=10,
        vertical="top"
    )
    comment.alignment = Alignment(
        vertical="top",
        horizontal="left",
        wrap_text=True,
        indent=1
    )

    # Light outline around


    # Border around comments area
    for row in ws["B24:J24"]:
        for cell in row:
            cell.border = Border(top=BORDER, bottom=BORDER)

    # End marker
    ws.merge_cells("B25:J25")
    write(
        ws, "B25", "*** END ***",
        bold=True, horizontal="center"
    )

    # Original printable region
    ws.print_area = "B1:J27"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    ws.page_margins = PageMargins(
        left=0.25, right=0.25,
        top=0.35, bottom=0.35,
        header=0.1, footer=0.1
    )

    ws.sheet_view.view = "pageBreakPreview"
    ws.sheet_view.zoomScale = 100
    ws.sheet_view.showGridLines = False

    output = REPORTS / (
        "Portable_Radiography_QC_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".xlsx"
    )


    # Prevent long labels from wrapping
    for address in ("B12", "B19", "B20"):
        ws[address].alignment = Alignment(
            vertical="center",
            wrap_text=False,
            shrink_to_fit=True
        )


    # Restore facility and equipment table borders
    for r, first, last in [(r, 2, 6) for r in range(10, 17)] + [(r, 8, 10) for r in range(8, 17)]:
        for c in range(first, last + 1):
            cell = ws.cell(r, c)
            cell.border = Border(
                left=BORDER if c == first else Side(),
                right=BORDER if c == last else Side(),
                top=BORDER,
                bottom=BORDER
            )


    # Match original cover fonts and gray table fill
    for address, size in [("B1",14), ("B2",14), ("B3",11)]:
        ws[address].font = Font(name="Calibri", size=size, bold=True)

    for row in range(10,17):
        for col in range(2,7):
            ws.cell(row,col).fill = PatternFill(
                "solid", fgColor="D9D9D9")
    for row in range(8,17):
        for col in range(8,11):
            ws.cell(row,col).fill = PatternFill(
                "solid", fgColor="D9D9D9")

    for row in range(10,17):
        ws[f"B{row}"].font = Font(
            name="Calibri", size=9 if row==12 else 11, bold=True)
        ws[f"C{row}"].font = Font(name="Calibri", size=11)

    for row in range(8,17):
        ws[f"H{row}"].font = Font(name="Calibri", size=11, bold=True)
        ws[f"J{row}"].font = Font(name="Calibri", size=11)


    # Vertical dividers and personnel field borders
    for r in range(10, 17):
        ws[f"C{r}"].border = Border(
            left=BORDER, top=BORDER, bottom=BORDER
        )

    for r in range(8, 17):
        ws[f"J{r}"].border = Border(
            left=BORDER, right=BORDER,
            top=BORDER, bottom=BORDER
        )

    for r in (19, 20):
        for c in range(2, 11):
            cell = ws.cell(r, c)
            cell.border = Border(
                left=BORDER if c in (2, 4) else Side(),
                right=BORDER if c == 10 else Side(),
                top=BORDER, bottom=BORDER
            )


    # State Form: reproduce the original layout from stored specifications.
    from services.state_form_layout import build_state_form
    # State Form: build from extracted original layout
    from services.state_form_layout import build_state_form
    state = wb.create_sheet("State Form")
    build_state_form(state)

    from services.state_form_layout import populate_state_form_equipment
    populate_state_form_equipment(state, info)

    from services.qc_data import load_qc_data
    from services.state_form_layout import populate_state_form_reproducibility

    populate_state_form_reproducibility(
        state,
        load_qc_data()
    )


    from services.state_form_layout import populate_state_form_hvl
    populate_state_form_hvl(state, load_qc_data())

    from services.state_form_layout import populate_state_form_kvp_accuracy
    populate_state_form_kvp_accuracy(state, load_qc_data())
    from services.state_form_layout import populate_state_form_ese_table
    populate_state_form_ese_table(state)

    from services.state_form_layout import populate_state_form_techniques
    populate_state_form_techniques(state, load_qc_data())

    print("KVP DEBUG — immediately after population:")
    for address in ("J28", "K28", "L28", "K30", "K31", "K32", "K33", "K34"):
        print(address, repr(state[address].value))


    from services.rad_mode_layout import build_rad_mode

    rad_mode = wb.create_sheet("RAD MODE")
    from services.rad_mode_layout import apply_original_rad_mode_layout
    apply_original_rad_mode_layout(rad_mode)
    from services.rad_mode_layout import clean_rad_mode_historical_data
    clean_rad_mode_historical_data(rad_mode)
    from services.rad_mode_layout import populate_rad_mode_header
    populate_rad_mode_header(rad_mode, info)
    from services.rad_mode_layout import populate_rad_mode_reproducibility_linearity
    from services.rad_mode_layout import populate_rad_mode_four_setting_linearity
    from services.rad_mode_layout import populate_rad_mode_reproducibility
    populate_rad_mode_reproducibility(rad_mode, load_qc_data())
    populate_rad_mode_four_setting_linearity(rad_mode, load_qc_data())
    build_rad_mode(rad_mode, load_qc_data())

    from services.rad_mode_layout import populate_rad_mode_summary
    populate_rad_mode_summary(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_overall_summary
    from services.rad_mode_layout import populate_rad_mode_four_setting_kvp
    populate_rad_mode_four_setting_kvp(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_output_constancy
    from services.rad_mode_layout import apply_rad_mode_precision_fix
    from services.rad_mode_layout import remove_rad_mode_historical_inspection_data
    remove_rad_mode_historical_inspection_data(rad_mode)
    apply_rad_mode_precision_fix(rad_mode)
    from services.rad_mode_layout import populate_rad_mode_test1_details
    populate_rad_mode_test1_details(rad_mode, load_qc_data())
    from services.rad_mode_layout import restore_test1_result_formatting
    restore_test1_result_formatting(rad_mode)




    # RAD MODE: exact six-page print layout.
    from openpyxl.worksheet.pagebreak import Break, RowBreak

    rad_mode.print_area = "A1:L250"

    rad_mode.sheet_properties.pageSetUpPr.fitToPage = True
    rad_mode.page_setup.orientation = "portrait"
    rad_mode.page_setup.paperSize = rad_mode.PAPERSIZE_LETTER
    rad_mode.page_setup.fitToWidth = 1
    rad_mode.page_setup.fitToHeight = 0
    rad_mode.page_setup.scale = None

    # Each break occurs after the specified row.
    rad_mode.row_breaks = RowBreak()
    for last_row in (52, 106, 152, 195, 227):
        rad_mode.row_breaks.append(Break(id=last_row))

    rad_mode.sheet_view.view = "pageBreakPreview"
    rad_mode.sheet_view.showGridLines = False

    from services.rad_mode_layout import populate_rad_mode_test_summary
    from services.rad_mode_layout import populate_rad_mode_light_field_alignment
    populate_rad_mode_light_field_alignment(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_ese
    populate_rad_mode_ese(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_field_size
    populate_rad_mode_field_size(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_central_beam
    populate_rad_mode_central_beam(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_exposure_index
    populate_rad_mode_exposure_index(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_image_quality
    populate_rad_mode_image_quality(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_dap_accuracy
    populate_rad_mode_dap_accuracy(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_light_field_illuminance
    populate_rad_mode_light_field_illuminance(rad_mode, load_qc_data())
    from services.rad_mode_layout import populate_rad_mode_sid_accuracy
    populate_rad_mode_sid_accuracy(rad_mode, load_qc_data())
    populate_rad_mode_output_constancy(rad_mode, load_qc_data())
    populate_rad_mode_overall_summary(rad_mode)
    from services.rad_mode_layout import populate_rad_mode_safety_checklist
    populate_rad_mode_safety_checklist(rad_mode, load_qc_data())
    populate_rad_mode_test_summary(rad_mode)
    from services.state_form_layout import populate_state_form_master_safety
    populate_state_form_master_safety(state, rad_mode, load_qc_data())

    # State Form linearity and reproducibility assessments
    state["Q23"] = rad_mode["C73"].value
    state["P24"] = rad_mode["H59"].value
    state["Q24"] = rad_mode["D73"].value

    
    # Complete State Form identification fields from existing report data.
    state["S5"] = state["K5"].value

    # Preserve existing equipment identifiers unless the source
    # contains a verified value for each field.

    # Transfer measured C.V. results from RAD MODE.
    # Blank source measurements remain blank.
    for target, source_cell in (("P20", "E71"), ("P22", "I71")):
        value = rad_mode[source_cell].value
        state[target] = value if isinstance(value, (int, float)) else None

    
    # State Form test equipment identification
    from datetime import datetime as _datetime

    state["B3"] = "TEST EQUIPMENT:"

    _info = __import__("json").loads(
        DATA.read_text()
    )

    _equipment = str(_info.get("test_equipment") or "").strip()
    _serial = str(_info.get("test_equipment_serial") or "").strip()
    _calibration = str(_info.get("calibration_date") or "").strip()

    if _calibration:
        try:
            _calibration = _datetime.strptime(
                _calibration, "%Y-%m-%d"
            ).strftime("%m/%d/%Y")
        except ValueError:
            pass

    _parts = []
    if _equipment:
        _parts.append(_equipment)
    if _serial:
        _parts.append(f"S/N: {_serial}")
    if _calibration:
        _parts.append(f"CALIBRATION DATE: {_calibration}")

    state["F3"] = "; ".join(_parts) if _parts else None

    
    # Final State Form date formatting
    _date_format = r"[$-409]mmmm\ d\,\ yyyy;@"
    for _cell in ("K6", "K68"):
        state[_cell].number_format = _date_format

    wb.save(output)
    return output
