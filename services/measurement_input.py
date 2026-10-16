import math
import streamlit as st


def measurement_input(
    label,
    *,
    key,
    on_change=None,
    min_value=None,
    format=None,
    label_visibility="visible",
    **kwargs,
):
    """Text-based numeric input with numeric session-state compatibility."""

    text_key = f"_measurement_text_{key}"

    if text_key not in st.session_state:
        saved = st.session_state.get(key)

        if saved is None:
            st.session_state[text_key] = ""
        else:
            try:
                value = float(saved)
                st.session_state[text_key] = (
                    f"{value:g}" if math.isfinite(value) and value != 0 else ""
                )
            except (TypeError, ValueError):
                st.session_state[text_key] = ""

    def commit():
        raw = st.session_state[text_key].strip()

        if not raw:
            st.session_state[key] = 0.0
        else:
            try:
                value = float(raw)
            except ValueError:
                return

            if not math.isfinite(value):
                return

            if min_value is not None and value < min_value:
                return

            st.session_state[key] = value

        if on_change is not None:
            on_change()

    st.text_input(
        label,
        key=text_key,
        label_visibility=label_visibility,
        on_change=commit,
    )

    return float(st.session_state.get(key) or 0.0)
