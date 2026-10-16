import math


def calculate_central_beam_alignment(
    sid_cm,
    displacement_mm,
    visual_check,
    tolerance_percent=2.0,
):
    sid_cm = float(sid_cm)
    displacement_mm = float(displacement_mm)
    visual_check = str(visual_check).strip().upper()

    if not math.isfinite(sid_cm) or sid_cm <= 0:
        raise ValueError("SID must be positive.")

    if not math.isfinite(displacement_mm):
        raise ValueError("Displacement must be finite.")

    if visual_check not in ("Y", "N"):
        raise ValueError("Visual check must be Y or N.")

    error_percent = abs(displacement_mm) / (sid_cm * 10) * 100

    passed = error_percent < tolerance_percent and visual_check == "Y"

    return {
        "error_percent": error_percent,
        "limit_mm": sid_cm * 10 * tolerance_percent / 100,
        "result": "Pass" if passed else "FAIL",
    }
