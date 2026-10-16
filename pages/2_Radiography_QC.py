
# Nominal kVp settings shared by QC calculations.
nominal_kvp_values = [50, 60, 70, 80, 90, 100, 110, 120]
import math
import streamlit as st



from services.qc_data import save_qc_data, get_qc_section
from services.qc_results import update_qc_results
from calculations.reproducibility import calculate_reproducibility
from calculations.linearity import calculate_linearity
# ==========================================
# 1. SAVED MEASUREMENTS
# ==========================================
MEASUREMENT_KEYS = [
    "rep_exp1",
    "rep_exp2",
    "rep_exp3",
    "rep_exp4",
    "mas1",
    "mas2",
    "mas3",
    "mas4",
    "dose1",
    "dose2",
    "dose3",
    "dose4",
]
REP_KEYS = [
    "rep_exp1",
    "rep_exp2",
    "rep_exp3",
    "rep_exp4",
]
DEFAULTS = {
    "rep_exp1": 0.0,
    "rep_exp2": 0.0,
    "rep_exp3": 0.0,
    "rep_exp4": 0.0,
    "mas1": 10.0,
    "mas2": 20.0,
    "mas3": 40.0,
    "mas4": 0.0,
    "dose1": 0.0,
    "dose2": 0.0,
    "dose3": 0.0,
    "dose4": 0.0,
}
def initialize_measurements():
    saved = get_qc_section("radiography_qc")
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = float(
                saved.get(key, default)
            )
def autosave_measurements():
    initialize_measurements()
    values = {
        key: float(st.session_state[key])
        for key in MEASUREMENT_KEYS
    }
    current = dict(get_qc_section("radiography_qc"))
    current.update(values)
    save_qc_data("radiography_qc", current)
    update_qc_results()
initialize_measurements()
# ==========================================
# 2. PAGE TITLE
# ==========================================
st.title("Radiography QC Measurements")
st.caption(
    "Portable Radiography — Quality Control Testing"
)
st.info(
    "Existing saved measurements are retained. "
    "Confirm that all values belong to the current "
    "QC session before preparing a clinical report."
)
# ==========================================


def autosave_combined_output():
    nominal_values = [50, 60, 70, 80, 90, 100, 110, 120]

    kvp_values = dict(get_qc_section("kvp_accuracy"))
    ese_values = dict(get_qc_section("entrance_skin_exposure"))
    hvl_values = dict(get_qc_section("hvl"))

    for nominal in nominal_values:
        kvp_key = f"kvp_{nominal}"
        mas_key = f"ese_mas_{nominal}"
        exposure_key = f"ese_exposure_{nominal}"

        if kvp_key in st.session_state:
            kvp_values[kvp_key] = st.session_state[kvp_key]

        if mas_key in st.session_state:
            ese_values[mas_key] = st.session_state[mas_key]

        if exposure_key in st.session_state:
            ese_values[exposure_key] = st.session_state[exposure_key]

    distance_key = "ese_measurement_distance_in"
    if distance_key in st.session_state:
        ese_values[distance_key] = st.session_state[distance_key]

    if "hvl_80" in st.session_state:
        hvl_values["hvl_80"] = st.session_state["hvl_80"]

    if "tube_output_baseline" in st.session_state:
        ese_values["tube_output_baseline"] = st.session_state["tube_output_baseline"]
    if "tube_output_baseline_year" in st.session_state:
        ese_values["tube_output_baseline_year"] = st.session_state["tube_output_baseline_year"]
    for key in ("tube_output_technique_mas", "tube_output_copper_mm"):
        if key in st.session_state:
            ese_values[key] = st.session_state[key]

    save_qc_data("kvp_accuracy", kvp_values)
    save_qc_data("entrance_skin_exposure", ese_values)
    for nominal in [50, 60, 70, 80, 90, 100, 110, 120]:
        key = f"hvl_{nominal}"
        if key in st.session_state:
            hvl_values[key] = float(st.session_state[key])

    save_qc_data("hvl", hvl_values)



# Validate displayed text before calculating; never use a stale saved number.
def _qc_validate_inputs(required=(), positive=()):
    problems = []
    for key in required:
        raw = st.session_state.get("_qc_text_" + key)
        if raw is None:
            # A non-text widget or a field not yet initialized.
            value = st.session_state.get(key)
            raw = "" if value is None else str(value)
        raw = str(raw).strip()
        if not raw:
            problems.append(key + " (missing)")
            continue
        try:
            value = float(raw)
            if not math.isfinite(value) or (key in positive and value <= 0):
                raise ValueError
        except (ValueError, TypeError):
            problems.append(key + " (invalid)")
    if problems:
        st.warning("Enter valid measurements before calculating: " + ", ".join(problems))
        st.stop()

QC_TEST_NAMES = [
    "1. Exposure Reproducibility and Linearity",
    
    "2. kVp Accuracy and Tube Output",
    "3. Half-Value Layer (HVL)",
    "4. X-ray / Light Field Alignment",
    "5. Numerical Field Size Indicator Accuracy",
    "6. X-Ray Central Beam Alignment",
    "7. Exposure Index (EI)",
    "8. Image Quality Tests",
    "9. DAP Accuracy",
    "10. SID Accuracy",
    "11. Light Field Illuminance",
    "12. Entrance Skin Exposure (ESE)",
]


if "qc_selected_test" not in st.session_state:
    st.session_state["qc_selected_test"] = 0

with st.sidebar:
    st.markdown("### Radiography QC")

    with st.expander("QC Tests", expanded=True):
        selected = st.radio(
            "Select a test",
            options=range(len(QC_TEST_NAMES)),
            format_func=lambda i: QC_TEST_NAMES[i],
            key="qc_selected_test",
            label_visibility="collapsed",
        )


if st.session_state["qc_selected_test"] == 0:
    import pandas as pd
    import statistics

    st.header("Exposure Reproducibility and Linearity")
    st.caption(
        "Four exposure settings, each with exposure and time columns. "
        "Enter only measurements actually acquired."
    )

    saved = dict(get_qc_section("radiography_qc"))

    def qc_number(key, default=None):
        value = saved.get(key, default)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def positive(value):
        return (
            value is not None
            and math.isfinite(float(value))
            and float(value) > 0
        )

    # Existing exposure keys are retained for compatibility.
    exposure_keys = [
        ["rep_exp1", "rep_exp2", "rep_exp3", "rep_exp4"],
        ["dose1", "s2_exp2", "s2_exp3", "s2_exp4"],
        ["dose2", "s3_exp2", "s3_exp3", "s3_exp4"],
        ["dose3", "s4_exp2", "s4_exp3", "s4_exp4"],
    ]

    time_keys = [
        [f"s{i}_time{j}" for j in range(1, 5)]
        for i in range(1, 5)
    ]

    mas_keys = ["mas4", "mas1", "mas2", "mas3"]
    kvp_keys = [
        "linearity_kvp_1",
        "linearity_kvp_2",
        "linearity_kvp_3",
        "linearity_kvp_4",
    ]
    fs_keys = [f"s{i}_fs" for i in range(1, 5)]

    st.markdown("### Exposure Reproducibility and Linearity")

    st.caption(
        "Four exposure settings with aligned focal spot, "
        "mAs, kVp, exposure and time measurements."
    )

    def display_value(value):
        if value is None or value == "":
            return ""
        return str(value)

    def parse_number(value):
        if value is None:
            return None
        value = str(value).strip()
        if value.lower() in ("", "none", "nan"):
            return None
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (ValueError, TypeError):
            return None

    selected_fs = [
        str(saved.get(fs_keys[i]) or "")
        for i in range(4)
    ]

    grid_cols = [f"col_{i}" for i in range(8)]

    rows = [
        ["FS", "mAs"] * 4,
        [
            item
            for i in range(4)
            for item in (
                selected_fs[i],
                display_value(saved.get(mas_keys[i])),
            )
        ],
        [
            item
            for i in range(4)
            for item in (
                "kVp:",
                display_value(saved.get(kvp_keys[i])),
            )
        ],
        ["Exposure", "Time"] * 4,
        ["(mR)", "(ms)"] * 4,
    ]

    for trial in range(4):
        row = []
        for i in range(4):
            if i in (1, 3) and trial > 0:
                row.extend(["—", "—"])
            else:
                row.extend([
                    display_value(
                        saved.get(exposure_keys[i][trial])
                    ),
                    display_value(
                        saved.get(time_keys[i][trial])
                    ),
                ])
        rows.append(row)


    # Calculate results from the current measurement session.
    import statistics

    def qc_number(value):
        try:
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    def qc_mean(values):
        valid = [v for v in values if v is not None]
        return statistics.mean(valid) if valid else None

    def qc_cv(values):
        valid = [v for v in values if v is not None]
        if len(valid) < 2:
            return None
        mean = statistics.mean(valid)
        return statistics.stdev(valid) / mean if mean > 0 else None

    def qc_show(value, decimals=2):
        return "" if value is None else f"{value:.{decimals}f}"

    exposure_means = []
    time_means = []
    exposure_cvs = []
    time_cvs = []
    outputs = []
    kvp_errors = []

    for i in range(4):
        exposures = [
            qc_number(saved.get(key))
            for key in exposure_keys[i]
        ]
        times = [
            qc_number(saved.get(key))
            for key in time_keys[i]
        ]

        mean_exp = qc_mean(exposures)
        mean_time = qc_mean(times)
        mas = qc_number(saved.get(mas_keys[i]))

        exposure_means.append(mean_exp)
        time_means.append(mean_time)
        exposure_cvs.append(qc_cv(exposures))
        time_cvs.append(qc_cv(times))

        outputs.append(
            mean_exp / mas
            if mean_exp is not None and mas is not None
            else None
        )

        measured_kvp = qc_number(saved.get(kvp_keys[i]))
        nominal_kvp = qc_number(
            saved.get("linearity_kvp_nominal")
        )

        kvp_errors.append(
            abs(measured_kvp - nominal_kvp)
            if measured_kvp is not None
            and nominal_kvp is not None
            else None
        )

    average_row = []
    cv_row = []
    output_row = []
    kvp_error_row = []

    for i in range(4):
        average_row.extend([
            qc_show(exposure_means[i]),
            qc_show(time_means[i], 1),
        ])

        cv_row.extend([
            qc_show(exposure_cvs[i], 3),
            qc_show(time_cvs[i], 3),
        ])

        output_row.extend([
            qc_show(outputs[i], 3),
            "",
        ])

        kvp_error_row.extend([
            qc_show(kvp_errors[i], 2),
            "",
        ])

    valid_outputs = [v for v in outputs if v is not None]

    coefficient = None
    if len(valid_outputs) == 4:
        maximum = max(valid_outputs)
        minimum = min(valid_outputs)
        if maximum + minimum > 0:
            coefficient = (
                (maximum - minimum) /
                (maximum + minimum)
            )

    cl_row = [""] * 8
    if coefficient is not None:
        cl_row[0] = qc_show(coefficient, 4)
        cl_row[1] = (
            "Pass" if coefficient <= 0.10 else "FAIL"
        )

    max_error_row = [""] * 8
    if all(error is not None for error in kvp_errors):
        max_error = max(kvp_errors)
        max_error_row[0] = qc_show(max_error, 2)

        nominal = qc_number(
            saved.get("linearity_kvp_nominal")
        )
        if nominal is not None:
            max_error_row[2] = (
                f"{100 * max_error / nominal:.1f}%"
            )

    # Three independent acceptance evaluations.
    reproducibility_pass = (
        exposure_cvs[0] is not None
        and exposure_cvs[0] <= 0.05
    )

    linearity_pass = (
        coefficient is not None
        and coefficient <= 0.10
    )

    nominal = qc_number(saved.get("linearity_kvp_nominal"))
    relative_kvp_error = (
        max(kvp_errors) / nominal
        if nominal is not None
        and all(error is not None for error in kvp_errors)
        else None
    )

    kvp_pass = (
        relative_kvp_error is not None
        and relative_kvp_error <= 0.05
    )

    reproducibility_row = [""] * 8
    reproducibility_row[0] = (
        "Pass" if reproducibility_pass else "FAIL"
    ) if exposure_cvs[0] is not None else "Incomplete"

    kvp_result_row = [""] * 8
    kvp_result_row[0] = (
        "Pass" if kvp_pass else "FAIL"
    ) if relative_kvp_error is not None else "Incomplete"

    overall_row = [""] * 8
    complete = (
        exposure_cvs[0] is not None
        and coefficient is not None
        and relative_kvp_error is not None
    )

    overall_row[0] = (
        "Pass" if (
            reproducibility_pass
            and linearity_pass
            and kvp_pass
        ) else "FAIL"
    ) if complete else "Incomplete"

    rows.extend([
        average_row,
        cv_row,
        output_row,
        cl_row,
        kvp_error_row,
        max_error_row,
        reproducibility_row,
        kvp_result_row,
        overall_row,
    ])

    labels = [
        "", "", "", "", "Trial",
        "1", "2", "3", "4",
        "Average", "C. V.", "mR/mAs",
        "C. L.", "kVp Error", "max kVp Error",
        "CV Result",
        "kVp Accuracy Result",
        "Overall Test 1",
    ]

    table_rows = []
    for label, values in zip(labels, rows):
        row = {"Row": label}
        row.update(dict(zip(grid_cols, values)))
        table_rows.append(row)

    table = pd.DataFrame(table_rows)

    column_config = {
        "Row": st.column_config.TextColumn(
            " ", width="small"
        )
    }

    for col in grid_cols:
        column_config[col] = st.column_config.TextColumn(
            " ", width="small"
        )

    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    grid_builder = GridOptionsBuilder.from_dataframe(table)

    grid_builder.configure_default_column(
        editable=False,
        resizable=True,
        sortable=False,
        filter=False,
        minWidth=90,
    )

    grid_builder.configure_column(
        "Row",
        headerName="",
        editable=False,
        pinned="left",
        width=90,
    )

    for i, col in enumerate(grid_cols):
        is_exposure = i % 2 == 0
        setting = i // 2

        editable = JsCode(f"""
        function(params) {{
            const r = params.node.rowIndex;

            if (r === 1) return true;

            if (r === 2) return {str(not is_exposure).lower()};

            if (r >= 5 && r <= 8) {{
                if ({setting} === 1 || {setting} === 3) {{
                    return r === 5;
                }}
                return true;
            }}

            return false;
        }}
        """)

        editor = JsCode(f"""
        function(params) {{
            if (
                params.node.rowIndex === 1 &&
                {str(is_exposure).lower()}
            ) {{
                return {{
                    component: 'agSelectCellEditor',
                    params: {{
                        values: ['small', 'large']
                    }}
                }};
            }}

            return {{
                component: 'agTextCellEditor'
            }};
        }}
        """)

        style = JsCode(f"""
        function(params) {{
            const r = params.node.rowIndex;
            const locked =
                r >= 6 && r <= 8 &&
                ({setting} === 1 || {setting} === 3);

            if (locked) {{
                return {{borderRight: "1px solid #888888", 
                    backgroundColor: '#d9d9d9',
                    color: '#777777'
                }};
            }}

            return {{borderRight: "1px solid #888888", }};
        }}
        """)

        result_style = JsCode("""
        function(params) {
            const value = String(params.value || "").trim().toLowerCase();

            if (value === "pass") {
                return {
                    backgroundColor: "#fff2a8",
                    color: "#665000",
                    fontWeight: "bold",
                    borderRight: "1px solid #888888"
                };
            }

            if (value === "fail") {
                return {
                    backgroundColor: "#ffb8b8",
                    color: "#8b0000",
                    fontWeight: "bold",
                    borderRight: "1px solid #888888"
                };
            }

            return {
                borderRight: "1px solid #888888"
            };
        }
        """)

        grid_builder.configure_column(
            col,
            headerName="",
            editable=editable,
            cellEditorSelector=editor,
            cellStyle=result_style,
            width=105,
            minWidth=90,
            maxWidth=160,
            cellClass="qc-grid-cell",
        )

    options = grid_builder.build()
    options["headerHeight"] = 0
    options["domLayout"] = "autoHeight"
    options["suppressHorizontalScroll"] = False



    options["suppressMovableColumns"] = True
    options["singleClickEdit"] = True
    options["stopEditingWhenCellsLoseFocus"] = True

    st.markdown(
        """
        <style>
        div[data-testid="stCustomComponent"] .ag-cell {
            border-right: 1px solid #b8bec7 !important;
            border-bottom: 1px solid #b8bec7 !important;
            padding-left: 8px !important;
            padding-right: 8px !important;
        }
        div[data-testid="stCustomComponent"] .ag-header-cell {
            border-right: 1px solid #b8bec7 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )




    options["suppressHorizontalScroll"] = False

    def render_qc_grid(expanded=False):
        grid_options = dict(options)
        grid_options["domLayout"] = "normal" if expanded else "autoHeight"

        response = AgGrid(
            table,
            gridOptions=grid_options,
            update_on=["cellValueChanged"],
            allow_unsafe_jscode=True,
            height=650 if expanded else 465,
            theme="streamlit",
            fit_columns_on_grid_load=False,
            key="qc_grid_expanded" if expanded else "qc_excel_style_aggrid_v2",
        )

        edited = pd.DataFrame(response["data"])

        updated = dict(saved)

        for i in range(4):
            exp_col = grid_cols[2*i]
            time_col = grid_cols[2*i + 1]

            fs_value = edited.at[1, exp_col]
            updated[fs_keys[i]] = (
                "" if pd.isna(fs_value) else str(fs_value)
            )

            updated[mas_keys[i]] = parse_number(
                edited.at[1, time_col]
            )

            updated[kvp_keys[i]] = parse_number(
                edited.at[2, time_col]
            )

            for trial in range(4):
                exp_key = exposure_keys[i][trial]
                time_key = time_keys[i][trial]

                if i in (1, 3) and trial > 0:
                    updated[exp_key] = None
                    updated[time_key] = None
                    continue

                updated[exp_key] = parse_number(
                    edited.at[trial + 5, exp_col]
                )
                updated[time_key] = parse_number(
                    edited.at[trial + 5, time_col]
                )

        if updated != saved:
            save_qc_data("radiography_qc", updated)
            st.rerun()

    @st.dialog("Exposure Reproducibility and Linearity", width="large")
    def expanded_qc_table():
        st.caption("Edit measurements here. Changes are saved automatically.")
        render_qc_grid(expanded=True)

    if st.button("⛶ Maximize Table", key="maximize_qc_table"):
        expanded_qc_table()

    render_qc_grid(expanded=False)


if st.session_state["qc_selected_test"] == 1:
    # 5. COMBINED KVP AND TUBE OUTPUT MEASUREMENTS
    # ==========================================
    st.divider()
    st.header("2. kVp Accuracy and Tube Output")

    st.write(
        "Enter the measurements collected together during the "
        "kVp accuracy and tube-output procedure."
    )

    nominal_kvp_values = [50, 60, 70, 80, 90, 100, 110, 120]

    saved_kvp = get_qc_section("kvp_accuracy")
    saved_ese = get_qc_section("entrance_skin_exposure")
    saved_hvl = get_qc_section("hvl")

    for nominal in nominal_kvp_values:
        defaults = {
            f"kvp_{nominal}": get_qc_section("kvp_accuracy").get(f"kvp_{nominal}", 0.0),
            f"ese_exposure_{nominal}": saved_ese.get(
                f"ese_exposure_{nominal}", 0.0
            ),
            f"ese_mas_{nominal}": saved_ese.get(
                f"ese_mas_{nominal}", 25.0
            ),
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = float(value)

    if "ese_measurement_distance_in" not in st.session_state:
        st.session_state["ese_measurement_distance_in"] = float(
            saved_ese.get("ese_measurement_distance_in", 100 / 2.54)
        )

    if "hvl_80" not in st.session_state:
        st.session_state["hvl_80"] = float(
            saved_hvl.get("hvl_80", 0.0)
        )




    _qc_key_672 = "ese_measurement_distance_in"
    if _qc_key_672 not in st.session_state:
        st.session_state[_qc_key_672] = 0.0

    _qc_text_key_672 = "_qc_text_" + str(_qc_key_672)

    if _qc_text_key_672 not in st.session_state:
        _qc_number_672 = st.session_state.get(_qc_key_672)
        st.session_state[_qc_text_key_672] = (
            "" if _qc_number_672 is None or _qc_number_672 == 0
            else str(_qc_number_672)
        )

    def _qc_commit_672(_qc_bound_key=_qc_key_672, _qc_bound_text_key=_qc_text_key_672):
        import math
        _qc_raw_672 = st.session_state[_qc_bound_text_key].strip()

        if not _qc_raw_672:
            st.session_state[_qc_bound_key] = 0.0
        else:
            try:
                _qc_number_672 = float(_qc_raw_672)
            except (ValueError, TypeError):
                return

            if not math.isfinite(_qc_number_672):
                return

            if _qc_number_672 < (0.01):
                return

            st.session_state[_qc_bound_key] = _qc_number_672

        (autosave_combined_output)()

    st.text_input(
        "Measurement distance (inches)",
        key=_qc_text_key_672,
        label_visibility="visible",
        on_change=_qc_commit_672,
    )

    st.caption(
        "Tube output is normalized to 100 cm. "
        "Measured kVp is used for kVp accuracy; "
        "nominal kVp is used for ESE regression."
    )

    saved_hvl = get_qc_section("hvl")
    for nominal in nominal_kvp_values:
        key = f"hvl_{nominal}"
        if key not in st.session_state:
            st.session_state[key] = float(saved_hvl.get(key, 0.0) or 0.0)

    # Nine-column kVp accuracy and tube-output table.
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    table_widths = [1.0, 1.3, 1.0, 1.1, 1.0, 1.3, 1.1, 1.2, 1.1]

    labels = [
        "kVp Setting",
        "kVp Measured",
        "kVp Error (kV)",
        "kVp rel. Error (%)",
        "mAs",
        "Exposure (mR)",
        "Factor to 100 cm",
        "Output (mR/mAs)",
        "HVL (mm Al)",
    ]

    headers = st.columns(table_widths, gap="small")
    for column, label in zip(headers, labels):
        column.markdown(f"**{label}**")

    distance_cm = (
        st.session_state["ese_measurement_distance_in"] * 2.54
    )
    distance_factor = (distance_cm / 100.0) ** 2

    relative_errors = []
    measured_outputs = []

    for nominal in nominal_kvp_values:
        columns = st.columns(table_widths, gap="small")

        columns[0].markdown(f"**{nominal}**")

        measured_text = columns[1].text_input(
            f"Measured kVp at {nominal}",
            value=str(st.session_state.get(f"kvp_{nominal}", "")),
            key=f"kvp_text_{nominal}",
            label_visibility="collapsed",
        )

        try:
            measured = float(measured_text) if measured_text.strip() else 0.0
            if not math.isfinite(measured) or measured < 0:
                raise ValueError
            st.session_state[f"kvp_{nominal}"] = measured
        except ValueError:
            measured = 0.0
            columns[1].error("Enter a valid nonnegative number.")

        if measured > 0:
            absolute_error = abs(nominal - measured)
            relative_error = 100.0 * absolute_error / nominal
            relative_errors.append(relative_error)

            columns[2].write(f"{absolute_error:.2f}")
            columns[3].write(f"{relative_error:.1f}%")
        else:
            columns[2].write("—")
            columns[3].write("—")

        mas_text = columns[4].text_input(
            f"mAs at {nominal}",
            value=str(st.session_state.get(f"ese_mas_{nominal}", "")),
            key=f"ese_mas_text_{nominal}",
            label_visibility="collapsed",
        )

        try:
            mas = float(mas_text) if mas_text.strip() else 0.0
            if not math.isfinite(mas) or mas < 0:
                raise ValueError
            st.session_state[f"ese_mas_{nominal}"] = mas
        except ValueError:
            mas = 0.0
            columns[4].error("Invalid mAs")

        exposure_text = columns[5].text_input(
            f"Exposure at {nominal}",
            value=str(st.session_state.get(f"ese_exposure_{nominal}", "")),
            key=f"ese_exposure_text_{nominal}",
            label_visibility="collapsed",
        )

        try:
            exposure = float(exposure_text) if exposure_text.strip() else 0.0
            if not math.isfinite(exposure) or exposure < 0:
                raise ValueError
            st.session_state[f"ese_exposure_{nominal}"] = exposure
        except ValueError:
            exposure = 0.0
            columns[5].error("Invalid exposure")

        columns[6].write(f"{distance_factor:.2f}")

        if exposure > 0 and mas > 0:
            output = exposure / mas * distance_factor
            measured_outputs.append(output)
            columns[7].write(f"{output:.2f}")
        else:
            columns[7].write("—")

        _qc_key_803 = f"hvl_{nominal}"
        if _qc_key_803 not in st.session_state:
            st.session_state[_qc_key_803] = 0.0

        _qc_text_key_803 = "_qc_text_" + str(_qc_key_803)

        if _qc_text_key_803 not in st.session_state:
            _qc_number_803 = st.session_state.get(_qc_key_803)
            st.session_state[_qc_text_key_803] = (
                "" if _qc_number_803 is None or _qc_number_803 == 0
                else str(_qc_number_803)
            )

        def _qc_commit_803(_qc_bound_key=_qc_key_803, _qc_bound_text_key=_qc_text_key_803):
            import math
            _qc_raw_803 = st.session_state[_qc_bound_text_key].strip()

            if not _qc_raw_803:
                st.session_state[_qc_bound_key] = 0.0
            else:
                try:
                    _qc_number_803 = float(_qc_raw_803)
                except (ValueError, TypeError):
                    return

                if not math.isfinite(_qc_number_803):
                    return

                if _qc_number_803 < (0.0):
                    return

                st.session_state[_qc_bound_key] = _qc_number_803

            (autosave_combined_output)()

        columns[8].text_input(
            f"HVL at {nominal} kVp (mm Al)",
            key=_qc_text_key_803,
            label_visibility="collapsed",
            on_change=_qc_commit_803,
        )

    save_qc_data(
        "kvp_accuracy",
        {
            f"kvp_{nominal}": st.session_state.get(f"kvp_{nominal}", 0.0)
            for nominal in nominal_kvp_values
        },
    )

    ese_values = dict(get_qc_section("entrance_skin_exposure"))

    for nominal in nominal_kvp_values:
        ese_values[f"ese_mas_{nominal}"] = st.session_state.get(
            f"ese_mas_{nominal}", 0.0
        )
        ese_values[f"ese_exposure_{nominal}"] = st.session_state.get(
            f"ese_exposure_{nominal}", 0.0
        )

    save_qc_data("entrance_skin_exposure", ese_values)

    # Baseline tube output and output constancy at 80 kVp.
    if "tube_output_baseline" not in st.session_state:
        st.session_state["tube_output_baseline"] = float(
            get_qc_section("entrance_skin_exposure").get(
                "tube_output_baseline", 0.0
            ) or 0.0
        )

    # Manually editable output technique, with defaults.
    _technique_defaults = {
        "tube_output_technique_mas": 25.0,
        "tube_output_copper_mm": 0.0,
    }

    _saved_technique = get_qc_section("entrance_skin_exposure")

    for _key, _default in _technique_defaults.items():
        if _key not in st.session_state:
            st.session_state[_key] = float(
                _saved_technique.get(_key, _default) or 0.0
            )

    _tech_cols = st.columns(2)

    _tech_cols[0].number_input(
        "Output technique (mAs)",
        min_value=0.0,
        step=1.0,
        format="%.1f",
        key="tube_output_technique_mas",
        on_change=autosave_combined_output,
    )

    _tech_cols[1].number_input(
        "Added copper filtration (mm Cu)",
        min_value=0.0,
        step=0.1,
        format="%.1f",
        key="tube_output_copper_mm",
        on_change=autosave_combined_output,
    )

    if "tube_output_baseline_year" not in st.session_state:
        st.session_state["tube_output_baseline_year"] = str(
            get_qc_section("entrance_skin_exposure").get(
                "tube_output_baseline_year", ""
            ) or ""
        )

    st.text_input(
        "Baseline year (YYYY)",
        key="tube_output_baseline_year",
        max_chars=4,
        on_change=autosave_combined_output,
        placeholder="e.g., 2025",
    )

    baseline = st.number_input(
        "Baseline tube output (mR/mAs)",
        min_value=0.0,
        step=0.01,
        format="%.3f",
        key="tube_output_baseline",
        on_change=autosave_combined_output,
    )

    exposure_80 = st.session_state.get("ese_exposure_80", 0.0)
    mas_80 = st.session_state.get("ese_mas_80", 0.0)

    if exposure_80 > 0 and mas_80 > 0:
        measured_output = exposure_80 / mas_80 * distance_factor
        st.metric("Measured tube output at 80 kVp", f"{measured_output:.3f} mR/mAs")

        if baseline > 0:
            change = abs(measured_output - baseline) / baseline * 100
            st.metric("Output change from baseline", f"{change:.2f}%")

            if change <= 10:
                st.success("Tube Output Constancy: PASS")
            else:
                st.error("Tube Output Constancy: FAIL")
        else:
            st.info("Enter the baseline output to assess tube output constancy.")
    else:
        st.info("Enter the 80-kVp exposure and mAs to calculate measured output.")

    st.divider()

    if len(relative_errors) == len(nominal_kvp_values):
        maximum_error = max(relative_errors)
        st.metric("Maximum kVp Relative Error", f"{maximum_error:.1f}%")
        if maximum_error <= 10.0:
            st.success("kVp Accuracy: PASS")
        else:
            st.error("kVp Accuracy: FAIL")
    else:
        st.info("Enter all eight measured kVp values to complete the kVp accuracy assessment.")

    st.caption(
        "HVL is measured separately. Missing measurements are shown as —, "
        "not as zero or as historical results."
    )

    # ==========================================

if st.session_state["qc_selected_test"] == 2:
    # 6. HALF-VALUE LAYER (HVL)
    # ==========================================
    st.divider()
    st.header("3. Half-Value Layer (HVL)")

    st.write(
        "Enter the HVL measured at 80 kVp. "
        "This measurement belongs to the same output procedure "
        "and is saved to the existing HVL section."
    )


    # HVL measurement: empty text field instead of a numeric zero.
    saved_hvl_value = get_qc_section("hvl").get("hvl_80")

    if "hvl_80_text" not in st.session_state:
        st.session_state["hvl_80_text"] = (
            str(saved_hvl_value)
            if saved_hvl_value is not None and float(saved_hvl_value) > 0
            else ""
        )

    hvl_text = st.text_input(
        "Measured HVL at 80 kVp (mm Al)",
        key="hvl_80_text",
        placeholder="Enter measured HVL",
    )

    measured_hvl = None

    if hvl_text.strip():
        try:
            parsed_hvl = float(hvl_text.strip())

            if not math.isfinite(parsed_hvl) or parsed_hvl <= 0:
                st.error("Enter a positive HVL measurement.")
            else:
                measured_hvl = parsed_hvl

                if saved_hvl_value is None or float(saved_hvl_value) != parsed_hvl:
                    save_qc_data("hvl", {"hvl_80": parsed_hvl})

                st.metric("Measured HVL", f"{measured_hvl:.2f} mm Al")

                if measured_hvl > 2.9:
                    st.success("HVL: PASS")
                else:
                    st.error("HVL: FAIL")

        except ValueError:
            st.error("Enter a valid numeric HVL measurement.")
    else:
        if saved_hvl_value is not None and float(saved_hvl_value) > 0:
            save_qc_data("hvl", {"hvl_80": 0.0})

        st.info("Enter the measured HVL to calculate the result.")


if st.session_state["qc_selected_test"] == 3:
    # 7. X-RAY / LIGHT FIELD ALIGNMENT
    # ==========================================
    st.divider()
    st.header("4. X-ray / Light Field Alignment")
    st.write(
        "Enter the four signed alignment errors in millimeters. "
        "The calculations follow the original Excel QC template."
    )
    saved_alignment = get_qc_section("light_field_alignment")
    alignment_fields = {
        "longitudinal_1": "Longitudinal error 1 (mm)",
        "longitudinal_2": "Longitudinal error 2 (mm)",
        "transverse_1": "Transverse error 1 (mm)",
        "transverse_2": "Transverse error 2 (mm)",
    }
    for key in alignment_fields:
        if key not in st.session_state:
            st.session_state[key] = float(
                saved_alignment.get(key, 0.0)
            )
    if "alignment_sid_cm" not in st.session_state:
        st.session_state["alignment_sid_cm"] = float(
            saved_alignment.get("alignment_sid_cm", 100.0)
        )
    def autosave_alignment():
        values = {
            key: float(st.session_state[key])
            for key in alignment_fields
        }
        values["alignment_sid_cm"] = float(
            st.session_state["alignment_sid_cm"]
        )
        save_qc_data("light_field_alignment", values)
    _qc_key_944 = "alignment_sid_cm"
    if _qc_key_944 not in st.session_state:
        st.session_state[_qc_key_944] = 0.0

    _qc_text_key_944 = "_qc_text_" + str(_qc_key_944)

    if _qc_text_key_944 not in st.session_state:
        _qc_number_944 = st.session_state.get(_qc_key_944)
        st.session_state[_qc_text_key_944] = (
            "" if _qc_number_944 is None or _qc_number_944 == 0
            else str(_qc_number_944)
        )

    def _qc_commit_944(_qc_bound_key=_qc_key_944, _qc_bound_text_key=_qc_text_key_944):
        import math
        _qc_raw_944 = st.session_state[_qc_bound_text_key].strip()

        if not _qc_raw_944:
            st.session_state[_qc_bound_key] = 0.0
        else:
            try:
                _qc_number_944 = float(_qc_raw_944)
            except (ValueError, TypeError):
                return

            if not math.isfinite(_qc_number_944):
                return

            if _qc_number_944 < (0.01):
                return

            st.session_state[_qc_bound_key] = _qc_number_944

        (autosave_alignment)()

    st.text_input(
        "Source-to-field distance (cm)",
        key=_qc_text_key_944,
        label_visibility="visible",
        on_change=_qc_commit_944,
    )
    columns = st.columns(2)
    for index, (key, label) in enumerate(alignment_fields.items()):
        with columns[index % 2]:
            _qc_key_954 = key
            if _qc_key_954 not in st.session_state:
                st.session_state[_qc_key_954] = 0.0

            _qc_text_key_954 = "_qc_text_" + str(_qc_key_954)

            if _qc_text_key_954 not in st.session_state:
                _qc_number_954 = st.session_state.get(_qc_key_954)
                st.session_state[_qc_text_key_954] = (
                    "" if _qc_number_954 is None or _qc_number_954 == 0
                    else str(_qc_number_954)
                )

            def _qc_commit_954(_qc_bound_key=_qc_key_954, _qc_bound_text_key=_qc_text_key_954):
                import math
                _qc_raw_954 = st.session_state[_qc_bound_text_key].strip()

                if not _qc_raw_954:
                    st.session_state[_qc_bound_key] = 0.0
                else:
                    try:
                        _qc_number_954 = float(_qc_raw_954)
                    except (ValueError, TypeError):
                        return

                    if not math.isfinite(_qc_number_954):
                        return

                    st.session_state[_qc_bound_key] = _qc_number_954

                (autosave_alignment)()

            st.text_input(
                label,
                key=_qc_text_key_954,
                label_visibility="visible",
                on_change=_qc_commit_954,
            )
    if st.button("Calculate Light Field Alignment"):
        # Validate the visible text, not the previous saved numeric values.
        # A genuine measured zero is valid for signed alignment errors.
        invalid = []
        for field_key, field_label in alignment_fields.items():
            raw = st.session_state.get("_qc_text_" + field_key, "").strip()
            try:
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError
            except (ValueError, TypeError):
                invalid.append(field_label)

        sid_raw = st.session_state.get("_qc_text_alignment_sid_cm", "").strip()
        try:
            sid_value = float(sid_raw)
            if not math.isfinite(sid_value) or sid_value <= 0:
                raise ValueError
        except (ValueError, TypeError):
            invalid.append("Source-to-field distance (cm), must be positive")

        if invalid:
            st.warning("Enter valid measurements before calculating: " + ", ".join(invalid))
            st.stop()

        sid_mm = st.session_state["alignment_sid_cm"] * 10
        longitudinal = (
            abs(st.session_state["longitudinal_1"])
            + abs(st.session_state["longitudinal_2"])
        ) / sid_mm
        transverse = (
            abs(st.session_state["transverse_1"])
            + abs(st.session_state["transverse_2"])
        ) / sid_mm
        a, b = st.columns(2)
        a.metric(
            "Longitudinal Error",
            f"{longitudinal * 100:.3f}%"
        )
        b.metric(
            "Transverse Error",
            f"{transverse * 100:.3f}%"
        )
        st.caption(
            "Acceptance criterion from the existing template: "
            "both errors must be less than 2% of SID."
        )
        if longitudinal < 0.02 and transverse < 0.02:
            st.success("PASS")
        else:
            st.error("FAIL")
    # ==========================================

if st.session_state["qc_selected_test"] == 4:
    # Excel-style Numerical Field Size Indicator Accuracy.
    st.divider()
    st.header("5. Numerical Field Size Indicator Accuracy")
    st.caption("All dimensions are in inches. Signed relative error is expressed as % of indicated SID. The 2% acceptance limit is provisional; confirm the applicable requirement before clinical use.")

    saved_field_size = dict(get_qc_section("field_size_accuracy"))
    field_defaults = {"measurement_distance_in": 39.37, "indicated_sid_in": 39.37}
    for i, size in enumerate((17.0, 12.0, 8.0), 1):
        for dim in ("length", "width"):
            field_defaults[f"selected_{dim}_{i}"] = size
            field_defaults[f"measured_{dim}_{i}"] = None

    def field_parse(raw, positive=True):
        try:
            if raw is None or not str(raw).strip():
                return None
            number = float(str(raw).strip())
            if not math.isfinite(number) or (number <= 0 if positive else number < 0):
                return None
            return number
        except (ValueError, TypeError):
            return None

    def field_commit(field_key, widget_key):
        value = field_parse(st.session_state.get(widget_key))
        st.session_state[field_key] = value
        current = dict(get_qc_section("field_size_accuracy"))
        current[field_key] = value
        save_qc_data("field_size_accuracy", current)

    def field_input(container, field_key, label):
        widget_key = "_qc_text_" + field_key
        if widget_key not in st.session_state:
            # Retain the same text-widget keys used by the earlier conversion.
            value = st.session_state.get(field_key, saved_field_size.get(field_key, field_defaults[field_key]))
            st.session_state[widget_key] = "" if value is None or value == 0 else str(value)
        container.text_input(
            label,
            key=widget_key,
            label_visibility="collapsed",
            on_change=field_commit,
            args=(field_key, widget_key),
        )
        value = field_parse(st.session_state[widget_key])
        st.session_state[field_key] = value
        return value

    top = st.columns([1.1, 1.1, 1.2, 1.2])
    top[0].markdown("**Measured at (in)**")
    measured_at = field_input(top[1], "measurement_distance_in", "Measurement distance (inches)")
    top[2].markdown("**SID (in)**")
    sid = field_input(top[3], "indicated_sid_in", "Indicated SID (inches)")

    st.markdown("**Numerical field size indicator accuracy**")
    widths = [1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 0.9, 0.9]
    group = st.columns(widths, gap="small")
    group[0].markdown("**Set**")
    group[2].markdown("**Measured**")
    group[4].markdown("**Rel. Error (% SID)**")
    group[6].markdown("**P/F**")
    header = st.columns(widths, gap="small")
    for col, title in zip(header, ("Longit.", "Transv.", "Longit.", "Transv.", "Longit.", "Transv.", "Longit.", "Transv.")):
        col.caption(title)

    all_results = []
    for setting in range(1, 4):
        cols = st.columns(widths, gap="small")
        for j, dimension in enumerate(("length", "width")):
            selected = field_input(cols[j], f"selected_{dimension}_{setting}", f"Selected {dimension} {setting}")
            measured = field_input(cols[j + 2], f"measured_{dimension}_{setting}", f"Measured {dimension} {setting}")
            if sid is None or measured_at is None or selected is None or measured is None:
                cols[j + 4].write("—")
                cols[j + 6].write("—")
                all_results.append(None)
            else:
                # Match the original worksheet: signed deviation / indicated SID.
                error_pct = (measured - selected) / sid * 100.0
                passed = abs(error_pct) <= 2.0
                cols[j + 4].write(f"{error_pct:.2f}%")
                cols[j + 6].write("Pass" if passed else "FAIL")
                all_results.append(passed)

    if any(result is None for result in all_results):
        st.info("Overall P/F: INCOMPLETE — enter all selected and measured dimensions, measurement distance, and SID.")
    elif all(all_results):
        st.success("Overall P/F: PASS — all six dimensions meet the provisional 2% limit.")
    else:
        st.error("Overall P/F: FAIL — at least one dimension exceeds the provisional 2% limit.")

if st.session_state["qc_selected_test"] == 5:
    # 9. X-RAY CENTRAL BEAM ALIGNMENT
    # ==========================================
    from calculations.central_beam_alignment import calculate_central_beam_alignment
    st.divider()
    st.header("6. X-Ray Central Beam Alignment")
    st.write(
        "Enter the SID, measured center displacement, and whether the BB "
        "is within the largest circle of the alignment tool."
    )
    st.caption(
        "The 2% SID criterion is preliminary. The original template's visual "
        "check alone determines Pass/FAIL; this application also evaluates "
        "the entered displacement. Verify the appropriate test method and "
        "acceptance criterion before clinical use."
    )
    CENTRAL_BEAM_DEFAULTS = {
        "central_beam_sid_cm": 100.0,
        "central_beam_displacement_mm": 0.0,
        "central_beam_visual_check": "",
    }
    saved_central_beam = get_qc_section("central_beam_alignment")
    for field_key, field_default in CENTRAL_BEAM_DEFAULTS.items():
        if field_key not in st.session_state:
            saved_value = saved_central_beam.get(field_key, field_default)
            if field_key == "central_beam_visual_check":
                saved_value = str(saved_value).strip().upper()
                if saved_value not in ("", "Y", "N"):
                    saved_value = ""
            else:
                saved_value = float(saved_value)
            st.session_state[field_key] = saved_value
    def autosave_central_beam():
        save_qc_data(
            "central_beam_alignment",
            {
                "central_beam_sid_cm": float(st.session_state["central_beam_sid_cm"]),
                "central_beam_displacement_mm": float(
                    st.session_state["central_beam_displacement_mm"]
                ),
                "central_beam_visual_check": st.session_state["central_beam_visual_check"],
            },
        )
    beam_sid_col, beam_displacement_col = st.columns(2)
    with beam_sid_col:
        _qc_key_1167 = "central_beam_sid_cm"
        if _qc_key_1167 not in st.session_state:
            st.session_state[_qc_key_1167] = 0.0

        _qc_text_key_1167 = "_qc_text_" + str(_qc_key_1167)

        if _qc_text_key_1167 not in st.session_state:
            _qc_number_1167 = st.session_state.get(_qc_key_1167)
            st.session_state[_qc_text_key_1167] = (
                "" if _qc_number_1167 is None or _qc_number_1167 == 0
                else str(_qc_number_1167)
            )

        def _qc_commit_1167(_qc_bound_key=_qc_key_1167, _qc_bound_text_key=_qc_text_key_1167):
            import math
            _qc_raw_1167 = st.session_state[_qc_bound_text_key].strip()

            if not _qc_raw_1167:
                st.session_state[_qc_bound_key] = 0.0
            else:
                try:
                    _qc_number_1167 = float(_qc_raw_1167)
                except (ValueError, TypeError):
                    return

                if not math.isfinite(_qc_number_1167):
                    return

                if _qc_number_1167 < (0.01):
                    return

                st.session_state[_qc_bound_key] = _qc_number_1167

            (autosave_central_beam)()

        st.text_input(
            "Central beam SID (cm)",
            key=_qc_text_key_1167,
            label_visibility="visible",
            on_change=_qc_commit_1167,
        )
    with beam_displacement_col:
        _qc_key_1175 = "central_beam_displacement_mm"
        if _qc_key_1175 not in st.session_state:
            st.session_state[_qc_key_1175] = 0.0

        _qc_text_key_1175 = "_qc_text_" + str(_qc_key_1175)

        if _qc_text_key_1175 not in st.session_state:
            _qc_number_1175 = st.session_state.get(_qc_key_1175)
            st.session_state[_qc_text_key_1175] = (
                "" if _qc_number_1175 is None or _qc_number_1175 == 0
                else str(_qc_number_1175)
            )

        def _qc_commit_1175(_qc_bound_key=_qc_key_1175, _qc_bound_text_key=_qc_text_key_1175):
            import math
            _qc_raw_1175 = st.session_state[_qc_bound_text_key].strip()

            if not _qc_raw_1175:
                st.session_state[_qc_bound_key] = 0.0
            else:
                try:
                    _qc_number_1175 = float(_qc_raw_1175)
                except (ValueError, TypeError):
                    return

                if not math.isfinite(_qc_number_1175):
                    return

                if _qc_number_1175 < (0.0):
                    return

                st.session_state[_qc_bound_key] = _qc_number_1175

            (autosave_central_beam)()

        st.text_input(
            "Center displacement (mm)",
            key=_qc_text_key_1175,
            label_visibility="visible",
            on_change=_qc_commit_1175,
        )
    st.selectbox(
        "BB within largest circle?",
        options=("", "Y", "N"),
        format_func=lambda value: {
            "": "Select visual check",
            "Y": "Yes (Y)",
            "N": "No (N)",
        }[value],
        key="central_beam_visual_check",
        on_change=autosave_central_beam,
    )
    if st.button("Calculate Central Beam Alignment"):
        _qc_validate_inputs(required=["central_beam_sid_cm", "central_beam_displacement_mm"], positive=["central_beam_sid_cm"])
        if st.session_state["central_beam_visual_check"] not in ("Y", "N"):
            st.warning("Select Y or N for the visual check before calculating.")
        else:
            try:
                beam_result = calculate_central_beam_alignment(
                    sid_cm=st.session_state["central_beam_sid_cm"],
                    displacement_mm=st.session_state["central_beam_displacement_mm"],
                    visual_check=st.session_state["central_beam_visual_check"],
                )
                a, b = st.columns(2)
                a.metric("Alignment error", f"{beam_result['error_percent']:.3f}%")
                b.metric("2% SID displacement limit", f"{beam_result['limit_mm']:.2f} mm")
                if beam_result["result"] == "Pass":
                    st.success("PASS — provisional combined displacement and visual check.")
                else:
                    st.error("FAIL — displacement or visual check did not meet the provisional criterion.")
            except (TypeError, ValueError) as error:
                st.warning(str(error))
    # ==========================================

if st.session_state["qc_selected_test"] == 6:
    # Test 7 — Exposure Index, compact layout corresponding to RAD MODE rows 153–171.
    st.divider()
    st.header("7. Exposure Index (EI)")
    st.caption("IEC 62494-1 · RQA5 surrogate: 70 ± 2.45 kVp, HVL 6.8 ± 0.25 mm Al. "
               "Displayed EI should be within ±20% of 100 × measured air kerma (µGy).")
    st.caption("Example setup: SID 140 cm; 70 kVp; 0.5 mm Cu + 2 mm Al; full detector irradiated. "
               "Confirm actual test conditions and acceptance criteria before clinical reporting.")

    ei_saved = dict(get_qc_section("exposure_index"))

    def ei_field(key, label, *, positive=False, nonnegative=False):
        # Keep the original numeric storage keys while using blank-friendly text widgets.
        text_key = "ei_table_text_" + key
        if text_key not in st.session_state:
            stored = ei_saved.get(key)
            st.session_state[text_key] = "" if stored is None or stored == "" else str(stored)

        def commit(bound_key=key, bound_text=text_key):
            raw = st.session_state[bound_text].strip()
            new_data = dict(get_qc_section("exposure_index"))
            try:
                value = float(raw) if raw else None
                if value is not None and (not math.isfinite(value) or
                        (positive and value <= 0) or (nonnegative and value < 0)):
                    value = None
            except (TypeError, ValueError):
                value = None
            # An invalid or cleared field must not leave an old value in storage.
            new_data[bound_key] = value
            save_qc_data("exposure_index", new_data)

        raw = st.text_input(label, key=text_key, label_visibility="collapsed", on_change=commit)
        try:
            val = float(raw.strip()) if raw.strip() else None
            if val is not None and (not math.isfinite(val) or
                    (positive and val <= 0) or (nonnegative and val < 0)):
                val = None
        except (TypeError, ValueError):
            val = None
        return val

    st.markdown("**Detector identification**")
    meta_cols = st.columns([1.4, 1, 1])
    meta_cols[0].markdown("**Detector**")
    meta_cols[1].markdown("**Serial number**")
    meta_cols[2].markdown("**CEID**")
    for detector, label in ((1, "#1 (Large)"), (2, "#2 (Small)")):
        cc = st.columns([1.4, 1, 1])
        cc[0].write(label)
        for col, suffix in ((1, "serial"), (2, "ceid")):
            key = f"ei_detector_{detector}_{suffix}"
            if key not in st.session_state:
                st.session_state[key] = str(ei_saved.get(key) or "")
            def save_meta(bound_key=key):
                data = dict(get_qc_section("exposure_index"))
                data[bound_key] = st.session_state[bound_key]
                save_qc_data("exposure_index", data)
            cc[col].text_input(key, key=key, label_visibility="collapsed", on_change=save_meta)

    st.markdown("**Measurements and calculations**")
    headers = ["Setup", "kVp", "mAs", "HVL (mm Al)", "Exposure (µR)",
               "Air kerma (µGy)", "Kerma × 100", "EI", "% Diff.", "DI", "P/F"]
    widths = [1.0, 1.05, 1.05, 1.35, 1.4, 1.1, 1.4, 1.3, 1.15, 1.05, 1.0]
    cc = st.columns(widths, gap="small")
    for col, label in zip(cc, headers):
        col.markdown(f"**{label}**")

    def static(col, value):
        col.write("—" if value is None else str(value))

    def ei_setting(key, label, default):
        # Editable acquisition settings with saved values and stable defaults.
        text_key = "ei_table_setting_" + key
        if text_key not in st.session_state:
            stored = ei_saved.get(key)
            st.session_state[text_key] = str(default if stored is None else stored)

        def commit(bound_key=key, bound_text=text_key):
            raw = st.session_state[bound_text].strip()
            try:
                value = float(raw) if raw else None
                if value is not None and (not math.isfinite(value) or value <= 0):
                    value = None
            except (ValueError, TypeError):
                value = None
            data = dict(get_qc_section("exposure_index"))
            data[bound_key] = value
            save_qc_data("exposure_index", data)

        raw = st.text_input(label, key=text_key, label_visibility="collapsed", on_change=commit)
        try:
            value = float(raw.strip()) if raw.strip() else None
            if value is None or not math.isfinite(value) or value <= 0:
                st.caption("Required")
        except (ValueError, TypeError):
            st.caption("Invalid")

    # Initial RQA5 dosimeter setup (reference HVL and exposure).
    cc = st.columns(widths, gap="small")
    static(cc[0], "Dos")
    with cc[1]:
        ei_setting("ei_reference_kvp", "Reference kVp", 70)
    with cc[2]:
        ei_setting("ei_reference_mas", "Reference mAs", 20)
    with cc[3]:
        hvl = ei_field("ei_hvl_mm_al", "Reference HVL", positive=True)
    with cc[4]:
        ref_exposure = ei_field("ei_reference_exposure_ur", "Reference exposure", positive=True)
    ref_kerma = ref_exposure / 114 if ref_exposure is not None else None
    static(cc[5], f"{ref_kerma:.2f}" if ref_kerma is not None else None)
    static(cc[6], f"{ref_kerma * 100:.2f}" if ref_kerma is not None else None)
    for col in cc[7:]:
        static(col, None)

    # Per-detector reference exposures are saved under the original app keys.
    detector_data = {}
    for detector in (1, 2):
        cc = st.columns(widths, gap="small")
        static(cc[0], f"Det #{detector}")
        with cc[1]:
            ei_setting(f"ei_detector_{detector}_kvp", f"Detector {detector} kVp", 70)
        with cc[2]:
            ei_setting(f"ei_detector_{detector}_mas", f"Detector {detector} mAs", 2)
        for col in cc[3:7]:
            static(col, None)
        with cc[7]:
            displayed = ei_field(f"ei_displayed_{detector}", f"Displayed EI {detector}", nonnegative=True)
        detector_data[detector] = {"displayed": displayed, "columns": cc}
        # Difference/results are written below after reference exposures are known.

    for detector, label in ((1, "Dos (L)"), (2, "Dos (S)")):
        cc = st.columns(widths, gap="small")
        static(cc[0], label)
        with cc[1]:
            ei_setting(f"ei_dosimeter_{detector}_kvp", f"Dosimeter {detector} kVp", 70)
        with cc[2]:
            ei_setting(f"ei_dosimeter_{detector}_mas", f"Dosimeter {detector} mAs", 2)
        static(cc[3], None)
        with cc[4]:
            exposure = ei_field(f"ei_exposure_{detector}_ur", f"Dosimeter exposure {detector}", positive=True)
        kerma = exposure / 114 if exposure is not None else None
        static(cc[5], f"{kerma:.2f}" if kerma is not None else None)
        static(cc[6], f"{kerma * 100:.2f}" if kerma is not None else None)
        for col in cc[7:]:
            static(col, None)
        detector_data[detector]["expected"] = kerma * 100 if kerma is not None else None

    def ei_di_input(detector, column):
        # DI is an editable observation, not part of the EI acceptance calculation.
        key = f"ei_detector_{detector}_di"
        widget_key = f"ei_table_di_{detector}"
        if widget_key not in st.session_state:
            saved_value = ei_saved.get(key)
            st.session_state[widget_key] = "N/A" if saved_value is None else str(saved_value)

        def save_di(bound_key=key, bound_widget=widget_key):
            data = dict(get_qc_section("exposure_index"))
            data[bound_key] = st.session_state[bound_widget].strip()
            save_qc_data("exposure_index", data)

        with column:
            st.text_input(f"Detector {detector} DI", key=widget_key,
                          label_visibility="collapsed", on_change=save_di)

    statuses = []
    for detector in (1, 2):
        entry = detector_data[detector]
        expected, displayed = entry["expected"], entry["displayed"]
        cc = entry["columns"]
        if expected is None or displayed is None:
            static(cc[8], None)
            ei_di_input(detector, cc[9])
            static(cc[10], "—")
            statuses.append(None)
        else:
            difference = (displayed - expected) / expected * 100
            passed = abs(difference) <= 20
            static(cc[8], f"{difference:+.1f}%")
            ei_di_input(detector, cc[9])
            static(cc[10], "Pass" if passed else "FAIL")
            statuses.append(passed)

    st.divider()
    hvl_pass = None if hvl is None else (6.55 <= hvl <= 7.05)
    hvl_cols = st.columns([2, 1])
    hvl_cols[0].write("RQA5 HVL P/F")
    hvl_cols[1].write("INCOMPLETE" if hvl_pass is None else ("Pass" if hvl_pass else "FAIL"))

    artifact_key = "ei_artifacts_noted"
    artifact_options = ["Not recorded", "No", "Yes"]
    if artifact_key not in st.session_state:
        existing = ei_saved.get(artifact_key, "Not recorded")
        st.session_state[artifact_key] = existing if existing in artifact_options else "Not recorded"
    def save_artifacts():
        data = dict(get_qc_section("exposure_index"))
        data[artifact_key] = st.session_state[artifact_key]
        save_qc_data("exposure_index", data)
    artifacts = st.selectbox("Artifacts noted", artifact_options, key=artifact_key, on_change=save_artifacts)

    # No result is issued for incomplete measurement sets.
    complete = all(x is not None for x in statuses) and hvl_pass is not None and artifacts != "Not recorded"
    if not complete:
        st.warning("Overall P/F: INCOMPLETE — enter both detector EI values, both dosimeter exposures, HVL, and artifact observation.")
    elif all(statuses) and hvl_pass and artifacts == "No":
        st.success("Overall P/F: PASS")
    else:
        st.error("Overall P/F: FAIL")
    st.caption("Acceptance uses symmetric ±20% EI difference and 6.55–7.05 mm Al HVL. "
               "These criteria and artifact handling require confirmation against the applicable QC protocol.")

if st.session_state["qc_selected_test"] == 7:
    st.divider()
    st.header("8. Image Quality Tests")
    st.caption("Enter measurements for the current QC session. The reviewer determines the overall result; no automatic acceptance threshold is assumed.")

    IQ_DETECTORS = ("small", "large")
    IQ_SPOTS = ("LFS", "SFS")
    IQ_OBSERVATIONS = ("", "Yes", "No", "N/A")
    IQ_ASSESSMENTS = ("Not assessed", "Pass", "FAIL")
    IQ_DEFAULTS = {"image_quality_assessment": "Not assessed", "image_quality_comments": ""}
    for iq_detector in IQ_DETECTORS:
        IQ_DEFAULTS[f"iq_{iq_detector}_serial"] = ""
        for iq_spot in IQ_SPOTS:
            prefix = f"iq_{iq_detector}_{iq_spot.lower()}"
            IQ_DEFAULTS.update({
                f"{prefix}_ei": 0.0, f"{prefix}_lp_mm": 0.0,
                f"{prefix}_lp_change": "", f"{prefix}_wedge": "",
                f"{prefix}_contrast": "", f"{prefix}_artifacts": "",
            })
            # New acquisition metadata is stored alongside the existing measurements.
            IQ_DEFAULTS.update({
                f"{prefix}_protocol": "ABDOMEN_AP",
                f"{prefix}_bucky": "table",
                f"{prefix}_grid": '40" focused',
                f"{prefix}_sid": '40"',
                f"{prefix}_kvp": "80",
                f"{prefix}_mas": "14" if iq_detector == "small" else "20",
                f"{prefix}_prior_lp": "N/A",
            })

    saved_iq = get_qc_section("image_quality")
    for key, default in IQ_DEFAULTS.items():
        if key not in st.session_state:
            value = saved_iq.get(key, default)
            if isinstance(default, float):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = default
            else:
                value = "" if value is None else str(value)
                if key.endswith(("_wedge", "_contrast", "_artifacts")) and value not in IQ_OBSERVATIONS:
                    value = ""
                if key == "image_quality_assessment" and value not in IQ_ASSESSMENTS:
                    value = "Not assessed"
            st.session_state[key] = value

    def autosave_image_quality():
        save_qc_data("image_quality", {key: st.session_state.get(key) for key in IQ_DEFAULTS})

    def iq_numeric_change(key, text_key):
        raw = st.session_state[text_key].strip()
        if not raw:
            st.session_state[key] = 0.0
        else:
            try:
                value = float(raw)
                if not math.isfinite(value) or value < 0:
                    return
            except (ValueError, TypeError):
                return
            st.session_state[key] = value
        autosave_image_quality()

    def iq_numeric_widget(container, key, label):
        text_key = "_qc_text_" + key
        if text_key not in st.session_state:
            existing = st.session_state.get(key, 0.0)
            st.session_state[text_key] = "" if existing is None or existing == 0 else str(existing)
        container.text_input(label, key=text_key, label_visibility="collapsed",
                             on_change=iq_numeric_change, args=(key, text_key))
        raw = st.session_state[text_key].strip()
        if raw:
            try:
                value = float(raw)
                if not math.isfinite(value) or value < 0:
                    raise ValueError
            except (ValueError, TypeError):
                container.caption("Invalid")

    for iq_detector in IQ_DETECTORS:
        st.subheader(f"{iq_detector.title()} detector")
        st.text_input("Detector serial number (optional)", key=f"iq_{iq_detector}_serial",
                      on_change=autosave_image_quality)

        st.markdown("**Acquisition settings**")
        acquisition_widths = [1.8, 1.0, 1.5, .8, .9, .65, .65, .85]
        cols = st.columns(acquisition_widths, gap="small")
        for col, title in zip(cols, ("Protocol", "Bucky", "Grid", "SID", "Spot", "kVp", "mAs", "Prior LP")):
            col.markdown(f"**{title}**")
        for spot in IQ_SPOTS:
            prefix = f"iq_{iq_detector}_{spot.lower()}"
            cols = st.columns(acquisition_widths, gap="small")
            for col, field, title in zip(
                (cols[0], cols[1], cols[2], cols[3]),
                ("protocol", "bucky", "grid", "sid"),
                ("Protocol", "Bucky", "Grid", "SID"),
            ):
                col.text_input(f"{iq_detector} {spot} {title}", key=f"{prefix}_{field}",
                               label_visibility="collapsed", on_change=autosave_image_quality)
            cols[4].write(spot)
            for col, field in ((cols[5], "kvp"), (cols[6], "mas"), (cols[7], "prior_lp")):
                col.text_input(f"{iq_detector} {spot} {field}", key=f"{prefix}_{field}",
                               label_visibility="collapsed", on_change=autosave_image_quality)

        st.markdown("**Image quality measurements**")
        measurement_widths = [.85, .8, .9, 1.05, 1.5, 1.55, 1.15]
        cols = st.columns(measurement_widths, gap="small")
        for col, title in zip(cols, ("Spot", "EI", "LP/mm", "LP change", "Al wedge distinct?", "12/16 C/D visible?", "Artifacts?")):
            col.markdown(f"**{title}**")
        for spot in IQ_SPOTS:
            prefix = f"iq_{iq_detector}_{spot.lower()}"
            cols = st.columns(measurement_widths, gap="small")
            cols[0].write(spot)
            iq_numeric_widget(cols[1], f"{prefix}_ei", f"{iq_detector} {spot} EI")
            iq_numeric_widget(cols[2], f"{prefix}_lp_mm", f"{iq_detector} {spot} LP/mm")
            cols[3].text_input(f"{iq_detector} {spot} LP change", key=f"{prefix}_lp_change",
                               label_visibility="collapsed", on_change=autosave_image_quality)
            for col, field in ((cols[4], "wedge"), (cols[5], "contrast"), (cols[6], "artifacts")):
                col.selectbox(f"{iq_detector} {spot} {field}", options=IQ_OBSERVATIONS,
                              format_func=lambda v: v or "—", key=f"{prefix}_{field}",
                              label_visibility="collapsed", on_change=autosave_image_quality)
        st.divider()

    st.text_area("Comments / artifact description", key="image_quality_comments",
                 on_change=autosave_image_quality)
    st.selectbox("Overall image-quality assessment (reviewer decision)",
                 options=IQ_ASSESSMENTS, key="image_quality_assessment",
                 on_change=autosave_image_quality)
    if st.session_state["image_quality_assessment"] == "Pass":
        st.success("Reviewer assessment: PASS (manual decision).")
    elif st.session_state["image_quality_assessment"] == "FAIL":
        st.error("Reviewer assessment: FAIL (manual decision).")
    else:
        st.info("Overall image-quality assessment: NOT ASSESSED")

if st.session_state["qc_selected_test"] == 8:
    # Test 9 — compact DAP accuracy table
    st.divider()
    st.header("9. DAP Accuracy")
    st.caption("Recommended: Displayed DAP should be within 30% of measured DAP.")
    st.write("**From table AEC measurements:**")

    _dap_defaults = {
        "dap_width_in": 17.0,
        "dap_height_in": 17.0,
        "dap_sid_cm": 101.6,
        "dap_kvp": 70.0,
        "dap_mas": 2.0,
        "dap_exposure_mr": None,
        "dap_displayed": None,
    }
    _dap_saved = get_qc_section("dap_accuracy")

    def _dap_store():
        _values = dict(get_qc_section("dap_accuracy"))
        for _name in _dap_defaults:
            _raw = st.session_state.get("dap_text_" + _name, "").strip()
            try:
                _num = float(_raw) if _raw else None
                _values[_name] = _num if _num is not None and math.isfinite(_num) else None
            except (TypeError, ValueError):
                _values[_name] = None
        save_qc_data("dap_accuracy", _values)

    def _dap_input(_col, _key, _label):
        _widget_key = "dap_text_" + _key
        if _widget_key not in st.session_state:
            _saved_value = _dap_saved.get(_key)
            if _saved_value is None:
                _saved_value = _dap_defaults[_key]
            st.session_state[_widget_key] = "" if _saved_value is None else str(_saved_value)
        _col.text_input(_label, key=_widget_key, label_visibility="collapsed", on_change=_dap_store)
        _raw = st.session_state[_widget_key].strip()
        if not _raw:
            return None
        try:
            _value = float(_raw)
            return _value if math.isfinite(_value) and _value > 0 else None
        except ValueError:
            return None

    # Wider measurement columns prevent numbers being clipped.
    _widths = [1.12, 1.12, 1.1, 0.95, 0.95, 1.1, 1.5]
    _headers = ["Collimat. X (in)", "Collimat. Y (in)", "SID (cm)", "kVp", "mAs", "X (mR)", "DAP (mGy·cm²)"]
    _head_cols = st.columns(_widths, gap="small")
    for _col, _label in zip(_head_cols, _headers):
        _col.markdown(f"**{_label}**")
    _cols = st.columns(_widths, gap="small")
    _x = _dap_input(_cols[0], "dap_width_in", "Collimation X")
    _y = _dap_input(_cols[1], "dap_height_in", "Collimation Y")
    _sid = _dap_input(_cols[2], "dap_sid_cm", "SID")
    _kvp = _dap_input(_cols[3], "dap_kvp", "kVp")
    _mas = _dap_input(_cols[4], "dap_mas", "mAs")
    _exposure = _dap_input(_cols[5], "dap_exposure_mr", "Exposure")
    _area = (_x * 2.54) * (_y * 2.54) if _x is not None and _y is not None else None
    _calculated = _exposure / 114.0 * _area if _exposure is not None and _area is not None else None
    _cols[6].write(f"{_calculated:.2f}" if _calculated is not None else "—")

    _bottom = st.columns([1.2, 1.2, 1.1, 1.0, 1.0, 1.1, 1.5], gap="small")
    _bottom[0].write("**Field area (cm²)**")
    _bottom[1].write(f"{_area:.2f}" if _area is not None else "—")
    _bottom[5].write("**Displayed DAP**")
    _displayed = _dap_input(_bottom[6], "dap_displayed", "Displayed DAP")

    _complete = all(_v is not None for _v in (_x, _y, _sid, _kvp, _mas, _exposure, _displayed))
    _difference = (100.0 * (_displayed - _calculated) / _calculated) if _complete and _calculated and _calculated > 0 else None
    _result = "INCOMPLETE" if _difference is None else ("PASS" if abs(_difference) < 30 else "FAIL")
    _results = st.columns([2, 1, 2, 1], gap="small")
    _results[0].write("**Difference**")
    _results[1].write(f"{_difference:+.1f}%" if _difference is not None else "—")
    _results[2].write("**Overall P/F**")
    _results[3].write(f"**{_result}**")
    if _result == "PASS":
        st.success("PASS — displayed DAP is within 30% of calculated DAP.")
    elif _result == "FAIL":
        st.error("FAIL — displayed DAP differs by 30% or more.")
    else:
        st.info("INCOMPLETE — enter all required valid measurements to calculate PASS/FAIL.")

    # ==========================================

if st.session_state["qc_selected_test"] == 9:
    # Test 10 — SID accuracy, compact Excel-style table.
    st.divider()
    st.header("10. SID Accuracy")
    st.caption("Acceptance: measured SID must be within 2% of set SID.")

    _sid_saved = get_qc_section("sid_accuracy")
    _sid_defaults = {
        "sid_indicator_type": "System tape",
        "sid_set_cm": 100.0,
        "sid_measured_cm": None,
    }

    def _sid_save():
        _data = dict(get_qc_section("sid_accuracy"))
        _data["sid_indicator_type"] = st.session_state.get("sid_table_indicator", "").strip()
        for _field in ("sid_set_cm", "sid_measured_cm"):
            _raw = st.session_state.get("sid_table_" + _field, "").strip()
            try:
                _value = float(_raw) if _raw else None
                _data[_field] = _value if _value is not None and math.isfinite(_value) and _value > 0 else None
            except (ValueError, TypeError):
                _data[_field] = None
        save_qc_data("sid_accuracy", _data)

    def _sid_text(_col, _field, _label):
        _widget = "sid_table_" + _field
        if _widget not in st.session_state:
            _value = _sid_saved.get(_field)
            if _value is None:
                _value = _sid_defaults[_field]
            st.session_state[_widget] = "" if _value is None else str(_value)
        _col.text_input(_label, key=_widget, label_visibility="collapsed", on_change=_sid_save)
        return st.session_state[_widget].strip()

    _widths = [1.8, 1.15, 1.0, 1.55, 1.55, 1.0]
    _headers = ["Indicator type", "Set SID (cm)", "2% SID (cm)",
                "SID measured (cm)", "Difference (% SID)", "P/F"]
    _heading = st.columns(_widths, gap="small")
    for _col, _label in zip(_heading, _headers):
        _col.markdown(f"**{_label}**")
    _row = st.columns(_widths, gap="small")
    if "sid_table_sid_indicator_type" not in st.session_state:
        st.session_state["sid_table_sid_indicator_type"] = (
            _sid_saved.get("sid_indicator_type") or "System tape"
        )

    _indicator = _sid_text(_row[0], "sid_indicator_type", "Indicator type")
    _set_raw = _sid_text(_row[1], "sid_set_cm", "Set SID")
    _measured_raw = _sid_text(_row[3], "sid_measured_cm", "Measured SID")

    def _sid_positive(_raw):
        try:
            _num = float(_raw)
            return _num if math.isfinite(_num) and _num > 0 else None
        except (ValueError, TypeError):
            return None

    _set = _sid_positive(_set_raw)
    _measured = _sid_positive(_measured_raw)
    from calculations.sid_accuracy import calculate_sid_accuracy

    _sid_result = (
        calculate_sid_accuracy(_set, _measured)
        if _indicator and _set is not None and _measured is not None
        else None
    )

    _tolerance = (
        _sid_result["tolerance_cm"] if _sid_result
        else 0.02 * _set if _set is not None else None
    )
    _difference = (
        _sid_result["difference_percent"] if _sid_result else None
    )
    _result = (
        _sid_result["result"].upper() if _sid_result else "INCOMPLETE"
    )
    _row[2].write(f"{_tolerance:.2f}" if _tolerance is not None else "—")
    _row[4].write(f"{_difference:.2f}%" if _difference is not None else "—")
    _row[5].write("—" if _result == "INCOMPLETE" else _result.title())

    if _result == "PASS":
        st.success("PASS — measured SID is within 2% of set SID.")
    elif _result == "FAIL":
        st.error("FAIL — measured SID differs by more than 2%.")
    else:
        st.info("INCOMPLETE — enter a valid indicator type, set SID, and measured SID.")

if st.session_state["qc_selected_test"] == 10:
    # 11. LIGHT FIELD ILLUMINANCE — COMPACT TABLE
    import math

    st.divider()
    st.header("11. Light Field Illuminance")
    st.caption("Measured at 100 cm or maximum SID.")

    keys = [
        "q1_lux", "q2_lux", "q3_lux",
        "q4_lux", "background_lux"
    ]

    saved = get_qc_section("light_field_illuminance")

    def save_illuminance():
        values = dict(get_qc_section("light_field_illuminance"))
        for key in keys:
            raw = st.session_state.get("_qc_text_" + key, "").strip()
            try:
                number = float(raw)
                if not math.isfinite(number) or number < 0:
                    raise ValueError
                values[key] = number
                st.session_state[key] = number
            except ValueError:
                values[key] = None
                st.session_state[key] = None
        save_qc_data("light_field_illuminance", values)

    def lux_input(key):
        text_key = "_qc_text_" + key
        if text_key not in st.session_state:
            previous = saved.get(key)
            if previous is None:
                previous = st.session_state.get(key)
            st.session_state[text_key] = (
                "" if previous is None or previous == ""
                else str(previous)
            )

        raw = st.text_input(
            key,
            key=text_key,
            label_visibility="collapsed",
            on_change=save_illuminance,
        ).strip()

        try:
            value = float(raw)
            if not math.isfinite(value) or value < 0:
                raise ValueError
            return value
        except ValueError:
            return None

    widths = [2.0, 1.3, 1.5]

    head = st.columns(widths)
    head[0].markdown("**Measurement**")
    head[1].markdown("**Region**")
    head[2].markdown("**lux**")

    measurements = [
        ("X-ray light field", "Q1 (TR)", "q1_lux"),
        ("", "Q2 (TL)", "q2_lux"),
        ("", "Q3 (BL)", "q3_lux"),
        ("", "Q4 (BR)", "q4_lux"),
        ("Background", "Center", "background_lux"),
    ]

    values = {}

    for description, region, key in measurements:
        cols = st.columns(widths, gap="small")
        cols[0].write(description)
        cols[1].write(region)
        with cols[2]:
            values[key] = lux_input(key)

    complete = all(value is not None for value in values.values())
    quadrants_positive = all(
        values[key] is not None and values[key] > 0
        for key in keys[:4]
    )

    if complete and quadrants_positive:
        average = sum(values[key] for key in keys[:4]) / 4
        corrected = average - values["background_lux"]
        state_result = "Pass" if corrected > 100 else "Fail"
        federal_result = "Pass" if corrected > 160 else "Fail"
    else:
        corrected = None
        state_result = "Incomplete"
        federal_result = "Incomplete"

    st.divider()
    result_cols = st.columns([2.2, 1.5, 1.3, 1.3])

    result_cols[0].markdown("**Average, corrected**")
    result_cols[1].markdown(
        f"**{corrected:.1f} lux**"
        if corrected is not None else "—"
    )
    result_cols[2].markdown("**Federal**")
    result_cols[3].markdown("**State**")

    status_cols = st.columns([2.2, 1.5, 1.3, 1.3])
    status_cols[0].write("Regulation")
    status_cols[1].write("")

    with status_cols[2]:
        if federal_result == "Pass":
            st.success("Pass")
        elif federal_result == "Fail":
            st.error("Fail")
        else:
            st.warning("Incomplete")

    with status_cols[3]:
        if state_result == "Pass":
            st.success("Pass")
        elif state_result == "Fail":
            st.error("Fail")
        else:
            st.warning("Incomplete")

    st.caption(
        "Worksheet criteria: Federal >160 lux; State >100 lux. "
        "Verify applicable requirements before clinical reporting."
    )


if st.session_state["qc_selected_test"] == 11:
    import math

    from calculations.ese import (
        calculate_ese_regression,
        calculate_patient_ese,
    )

    st.divider()
    st.header("12. Entrance Skin Exposure (ESE)")
    st.caption(
        "Calculated from the eight tube-output measurements in Test 2. "
        "Enter actual measurements before using results clinically."
    )

    ESE_KVP_VALUES = [50, 60, 70, 80, 90, 100, 110, 120]

    ESE_PROJECTIONS = [
        ("Chest (PA) grid", 23, 120, 4, 183, 35),
        ("Chest (PA) non-grid", 23, 85, 2.8, 183, 30),
        ("Abdomen (KUB)", 23, 75, 25, 100, 600),
        ("Lumbar Spine (AP)", 23, 85, 25, 100, 800),
        ("Cervical Spine (AP)", 13, 75, 6.3, 100, 200),
        ("Skull (LAT)", 15, 80, 6.3, 100, 250),
        ("Foot (D/P)", 8, 65, 3.2, 100, 100),
    ]

    saved_ese = get_qc_section("entrance_skin_exposure")

    def ese_input(key, default, label):
        text_key = "_qc_text_" + key

        if key not in st.session_state:
            try:
                st.session_state[key] = float(saved_ese.get(key, default))
            except (TypeError, ValueError):
                st.session_state[key] = float(default)

        if text_key not in st.session_state:
            st.session_state[text_key] = str(st.session_state[key])

        def commit():
            raw = st.session_state[text_key].strip()
            try:
                value = float(raw)
            except (ValueError, TypeError):
                return
            if not math.isfinite(value) or value < 0:
                return

            st.session_state[key] = value
            updated = dict(get_qc_section("entrance_skin_exposure"))
            updated[key] = value
            save_qc_data("entrance_skin_exposure", updated)

        st.text_input(
            label,
            key=text_key,
            label_visibility="collapsed",
            on_change=commit,
        )

        raw = st.session_state[text_key].strip()
        try:
            value = float(raw)
            return value if math.isfinite(value) and value >= 0 else None
        except (ValueError, TypeError):
            return None

    st.subheader("Regression parameters")

    exposures = []
    mas_values = []

    for nominal in ESE_KVP_VALUES:
        try:
            exposure = float(
                st.session_state.get(
                    f"ese_exposure_{nominal}",
                    saved_ese.get(f"ese_exposure_{nominal}", 0),
                )
            )
            mas = float(
                st.session_state.get(
                    f"ese_mas_{nominal}",
                    saved_ese.get(f"ese_mas_{nominal}", 0),
                )
            )
        except (ValueError, TypeError):
            exposure, mas = 0, 0

        exposures.append(exposure)
        mas_values.append(mas)

    distance_in = float(
        st.session_state.get(
            "ese_measurement_distance_in",
            saved_ese.get("ese_measurement_distance_in", 100 / 2.54),
        )
    )

    regression = None

    if (
        all(math.isfinite(v) and v > 0 for v in exposures + mas_values)
        and math.isfinite(distance_in)
        and distance_in > 0
    ):
        try:
            regression = calculate_ese_regression(
                kvp_values=ESE_KVP_VALUES,
                exposures_mr=exposures,
                mas_values=mas_values,
                distance_in=distance_in,
            )
        except (ValueError, TypeError, OverflowError) as error:
            st.warning(f"Regression unavailable: {error}")

    a, b, c = st.columns(3)

    with a:
        st.metric(
            "R (mR/mAs)",
            f"{regression['R']:.6f}" if regression else "—",
        )
    with b:
        st.metric(
            "Exponent X",
            f"{regression['X']:.6f}" if regression else "—",
        )
    with c:
        dpr = ese_input(
            "ese_dpr_in", 0,
            "DPR (inches)",
        )
        st.caption("DPR (inches)")

    if regression is None:
        st.info(
            "Complete all eight tube-output exposure and mAs "
            "measurements in Test 2 to calculate ESE."
        )

    st.subheader("Patient Entrance Skin Exposure")
    st.caption(
        "ESE = R × (kVp / 100)^X × mAs × (39.4 / D)^2. "
        "D is the focal-spot-to-skin distance."
    )

    widths = [2.8, 0.85, 0.85, 0.85, 0.85, 1.0, 1.0, 0.9, 0.75]

    headers = [
        "Projection", "PT (cm)", "kVp", "mAs",
        "SID (cm)", "SID (in)", "ESE (mR)",
        "ESE (Limit)", "P/F",
    ]

    cols = st.columns(widths, gap="small")
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    results = []

    for index, (name, thickness, kvp, mas, sid, limit) in enumerate(
        ESE_PROJECTIONS
    ):
        cols = st.columns(widths, gap="small")
        cols[0].write(name)

        values = []

        fields = [
            ("thickness", thickness),
            ("kvp", kvp),
            ("mas", mas),
            ("sid", sid),
        ]

        for col, (field, default) in zip(cols[1:5], fields):
            with col:
                values.append(
                    ese_input(
                        f"ese_patient_{field}_{index}",
                        default,
                        f"{name} {field}",
                    )
                )

        with cols[7]:
            ese_limit = ese_input(
                f"ese_patient_limit_{index}",
                limit,
                f"{name} ESE limit",
            )

        pt, kv, ma, sid_cm = values

        valid = (
            regression is not None
            and dpr is not None
            and all(v is not None and v > 0 for v in values)
            and ese_limit is not None
            and ese_limit > 0
        )

        if sid_cm is not None and sid_cm > 0:
            cols[5].write(f"{sid_cm / 2.54:.2f}")
        else:
            cols[5].write("—")

        if valid:
            try:
                result = calculate_patient_ese(
                    R=regression["R"],
                    X=regression["X"],
                    kvp=kv,
                    mas=ma,
                    sid_cm=sid_cm,
                    patient_thickness_cm=pt,
                    dpr_in=dpr,
                    ese_limit_mr=ese_limit,
                )

                ese = result["ese_mr"]
                status = result["result"]

                cols[6].write(f"{ese:.2f}")
                cols[8].write(status)

                results.append(status)

            except (ValueError, TypeError, OverflowError):
                cols[6].write("—")
                cols[8].write("—")
        else:
            cols[6].write("—")
            cols[8].write("—")

    st.divider()

    if len(results) == len(ESE_PROJECTIONS):
        if all(result == "Pass" for result in results):
            st.success("Overall P/F: PASS")
        else:
            st.error("Overall P/F: FAIL")
    else:
        st.info("Overall P/F: Pending complete measurements")
