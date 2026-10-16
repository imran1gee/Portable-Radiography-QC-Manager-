"""SID accuracy calculation matching the existing Excel template."""

import math


def calculate_sid_accuracy(set_sid_cm, measured_sid_cm):
    set_sid_cm = float(set_sid_cm)
    measured_sid_cm = float(measured_sid_cm)

    if not all(math.isfinite(x) for x in (set_sid_cm, measured_sid_cm)):
        raise ValueError("SID measurements must be finite numbers.")

    if set_sid_cm <= 0 or measured_sid_cm <= 0:
        raise ValueError("SID measurements must be positive.")

    difference_cm = abs(measured_sid_cm - set_sid_cm)
    tolerance_cm = 0.02 * set_sid_cm
    difference_percent = 100.0 * difference_cm / set_sid_cm

    passed = difference_cm < tolerance_cm

    return {
        "set_sid_cm": set_sid_cm,
        "measured_sid_cm": measured_sid_cm,
        "difference_cm": difference_cm,
        "tolerance_cm": tolerance_cm,
        "difference_percent": difference_percent,
        "result": "Pass" if passed else "FAIL",
    }
