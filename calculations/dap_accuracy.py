"""DAP accuracy calculations for portable radiography QC."""

import math


def calculate_dap_accuracy(
    width_in,
    height_in,
    exposure_mr,
    displayed_dap,
    tolerance=0.30,
):
    values = (
        width_in,
        height_in,
        exposure_mr,
        displayed_dap,
    )

    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("All DAP measurements must be finite.")

    if any(float(x) <= 0 for x in values):
        raise ValueError("All DAP measurements must be positive.")

    area_cm2 = float(width_in) * float(height_in) * 2.54**2

    measured_dap = float(exposure_mr) / 114.0 * area_cm2

    difference = (
        float(displayed_dap) - measured_dap
    ) / measured_dap

    return {
        "area_cm2": area_cm2,
        "measured_dap": measured_dap,
        "displayed_dap": float(displayed_dap),
        "difference_percent": difference * 100.0,
        "result": "Pass" if abs(difference) < tolerance else "FAIL",
    }
