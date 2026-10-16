import math


def calculate_exposure_index(
    exposure_ur,
    displayed_ei,
    tolerance_percent=20.0,
):
    exposure_ur = float(exposure_ur)
    displayed_ei = float(displayed_ei)

    if not all(math.isfinite(x) for x in (exposure_ur, displayed_ei)):
        raise ValueError("Measurements must be finite numbers.")

    if exposure_ur <= 0 or displayed_ei <= 0:
        raise ValueError("Exposure and displayed EI must be positive.")

    air_kerma_ugy = exposure_ur / 114.0
    expected_ei = air_kerma_ugy * 100.0

    difference_percent = (
        (displayed_ei - expected_ei) / expected_ei
    ) * 100.0

    passed = abs(difference_percent) < tolerance_percent

    return {
        "air_kerma_ugy": air_kerma_ugy,
        "expected_ei": expected_ei,
        "difference_percent": difference_percent,
        "absolute_difference_percent": abs(difference_percent),
        "result": "Pass" if passed else "FAIL",
    }
