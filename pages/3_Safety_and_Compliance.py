import streamlit as st
from services.qc_data import get_qc_section, save_qc_data


st.header("Master Safety and Compliance Checklist")
st.caption("One assessment per requirement — used by RAD MODE and State Form")

SAFETY_GROUPS = {
    "1. Timer and Exposure Switch": [
        ("deadman_switch", "Deadman type exposure switch"),
        ("preset_timer", "Preset timer terminates exposure"),
        ("timer_accuracy", "Timer accurate"),
        ("zero_setting", 'Exposure on "zero" setting not possible'),
    ],
    "2. Filtration and Tube Housing": [
        ("filtration", "Adequate filtration"),
        ("tube_stability", "Tube head stability"),
        ("tube_leakage", "Tube head leakage"),
        ("standby_leakage", "Standby leakage from capacitor-discharge unit"),
    ],
    "3. Technique Factors / Machine Performance": [
        ("technique_indicated", "Technique factors indicated"),
        ("kvp_accuracy", "Kilovolt indicator accurate"),
        ("linearity", "Exposures linear"),
        ("reproducibility", "Exposures reproducible"),
        ("aec_reproducibility", "AEC: exposure reproducible"),
        ("aec_mode", "AEC: mode indicated"),
        ("aec_backup", "AEC: back-up timer functions"),
        ("entrance_exposure", "Entrance exposures within specified limits"),
    ],
    "4. Safety Factors": [
        ("patient_visibility", "Patient visible from exposure position"),
        ("patient_communication", "Visual and oral communication with patient"),
        ("beam_indicator", "Beam-on indicator"),
        ("protective_apparel", "Protective apparel provided (as required)"),
        ("technique_guides", "Technique guides"),
    ],
    "5. Shielding": [
        ("operator_shielding", "Operator shielding adequate"),
        ("switch_shielding", "Exposure switch mounted behind shield"),
        ("mobile_cord", "Mobile equipment: 6-foot exposure cord"),
        ("room_shielding", "Room shielding adequate"),
        ("gonadal_shielding", "Gonadal shielding provided (as required)"),
    ],
    "6. Collimation": [
        ("collimator", "Collimating equipment adequate"),
        ("light_alignment", "X-ray / light alignment adequate"),
        ("beam_centering", "Beam centering satisfactory"),
        ("sid_accuracy", "SID indicator accurate"),
    ],
    "7. Additional Equipment Safety Requirements": [
        ('warning_label', 'Warning label present'),
        ('door_interlocks', 'All door interlocks functioning properly'),
        ('exposure_cables', 'All wires and cables in good condition'),
        ('perpendicular_indicator', 'Means to indicate when beam is perpendicular to image receptor'),
        ('minimum_field_size', 'Minimum field size less than 5 cm by 5 cm'),
        ('cassette_cleaning', 'Cassette cleaning date posted'),
        ('cassette_condition', 'General condition of cassettes acceptable'),
        ('mobile_operator_distance', 'Operator can stand more than 6 ft from x-ray tube'),
        ('minimum_ssd', 'Minimum SSD greater than 12 inches'),
    ],
}

STATUS_OPTIONS = [
    "Not assessed",
    "Compliant",
    "Non-compliant",
    "Not applicable",
]

saved_safety = get_qc_section("equipment_safety")

all_items = [
    (key, label)
    for items in SAFETY_GROUPS.values()
    for key, label in items
]

for key, label in all_items:
    status_key = "safety_status_" + key
    comment_key = "safety_comment_" + key

    if status_key not in st.session_state:
        previous = saved_safety.get(key, {})
        previous_status = previous.get(
            "status", "Not assessed"
        )
        st.session_state[status_key] = (
            previous_status
            if previous_status in STATUS_OPTIONS
            else "Not assessed"
        )

    if comment_key not in st.session_state:
        previous = saved_safety.get(key, {})
        st.session_state[comment_key] = previous.get(
            "comment", ""
        )

def autosave_safety():
    values = {
        key: {
            "status": st.session_state["safety_status_" + key],
            "comment": st.session_state["safety_comment_" + key],
        }
        for key, label in all_items
    }
    save_qc_data("equipment_safety", values)

st.info(
    "Select the observed inspection status. "
    "Not assessed is the default. "
    "Entries are saved automatically."
)


RAD_MODE_KEYS = {
    "warning_label", "tube_stability", "technique_indicated",
    "beam_indicator", "door_interlocks", "patient_visibility",
    "patient_communication", "switch_shielding", "deadman_switch",
    "exposure_cables", "perpendicular_indicator", "minimum_field_size",
    "technique_guides", "gonadal_shielding", "protective_apparel",
    "cassette_cleaning", "cassette_condition",
    "mobile_operator_distance", "minimum_ssd",
}

STATE_FORM_KEYS = {
    "deadman_switch", "preset_timer", "timer_accuracy",
    "zero_setting", "filtration", "tube_stability",
    "tube_leakage", "standby_leakage", "technique_indicated",
    "kvp_accuracy", "linearity", "reproducibility",
    "aec_reproducibility", "aec_mode", "aec_backup",
    "entrance_exposure", "patient_visibility",
    "patient_communication", "beam_indicator",
    "protective_apparel", "technique_guides",
    "operator_shielding", "switch_shielding",
    "mobile_cord", "room_shielding", "gonadal_shielding",
    "collimator", "light_alignment", "beam_centering",
    "sid_accuracy",
}

for group_title, items in SAFETY_GROUPS.items():
    st.subheader(group_title)

    for key, label in items:
        destinations = []
        if key in RAD_MODE_KEYS:
            destinations.append("RAD MODE")
        if key in STATE_FORM_KEYS:
            destinations.append("State Form")
        suffix = "  ·  " + " / ".join(destinations) if destinations else ""
        st.markdown("**" + label + "**" + suffix)

        col_status, col_comment = st.columns([1, 2])

        with col_status:
            st.selectbox(
                "Inspection status",
                STATUS_OPTIONS,
                key="safety_status_" + key,
                on_change=autosave_safety,
                label_visibility="collapsed",
            )

        with col_comment:
            st.text_input(
                "Comments — " + label,
                key="safety_comment_" + key,
                on_change=autosave_safety,
                placeholder="Optional observation or corrective action",
                label_visibility="collapsed",
            )

    st.divider()

statuses = [
    st.session_state["safety_status_" + key]
    for key, label in all_items
]

compliant = statuses.count("Compliant")
noncompliant = statuses.count("Non-compliant")
not_applicable = statuses.count("Not applicable")
not_assessed = statuses.count("Not assessed")

st.subheader("Inspection Summary")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Compliant", compliant)
c2.metric("Non-compliant", noncompliant)
c3.metric("N/A", not_applicable)
c4.metric("Not assessed", not_assessed)

if noncompliant:
    st.error(
        "One or more inspections are non-compliant. "
        "Review the findings and comments."
    )
elif not_assessed:
    st.warning(
        "Inspection is incomplete: some checks "
        "have not been assessed."
    )
else:
    st.success(
        "All checks have been assessed. "
        "Review any N/A decisions before reporting."
    )
