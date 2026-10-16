"""Entrance Skin Exposure calculations matching the QC Excel template."""

import math


def calculate_ese_regression(kvp_values, exposures_mr, mas_values, distance_in):
    """Fit output = R * (kVp / 100) ** X using eight measurements."""

    if not (
        len(kvp_values) == len(exposures_mr) == len(mas_values) == 8
    ):
        raise ValueError("Exactly eight kVp, exposure, and mAs values are required.")

    distance_in = float(distance_in)

    if not math.isfinite(distance_in) or distance_in <= 0:
        raise ValueError("Measurement distance must be positive.")

    x_values = []
    y_values = []
    outputs = []

    correction = (distance_in * 2.54 / 100.0) ** 2

    for kvp, exposure, mas in zip(kvp_values, exposures_mr, mas_values):
        kvp = float(kvp)
        exposure = float(exposure)
        mas = float(mas)

        if not all(math.isfinite(v) and v > 0 for v in (kvp, exposure, mas)):
            raise ValueError("All kVp, exposure, and mAs values must be positive.")

        output = correction * exposure / mas

        outputs.append(output)
        x_values.append(math.log(kvp / 100.0))
        y_values.append(math.log(output))

    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xx = sum(x * x for x in x_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))

    denominator = n * sum_xx - sum_x ** 2

    if abs(denominator) < 1e-12:
        raise ValueError("Regression cannot be calculated from these kVp values.")

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_xx * sum_y - sum_x * sum_xy) / denominator

    return {
        "R": math.exp(intercept),
        "X": slope,
        "outputs_mr_per_mas": outputs,
    }


def calculate_patient_ese(
    R,
    X,
    kvp,
    mas,
    sid_cm,
    patient_thickness_cm,
    dpr_in=0,
    ese_limit_mr=None,
):
    """Calculate ESE using the RAD MODE worksheet's patient formula."""

    values = (R, kvp, mas, sid_cm)

    if not all(math.isfinite(float(v)) and float(v) > 0 for v in values):
        raise ValueError("R, kVp, mAs, and SID must be positive.")

    X = float(X)
    patient_thickness_cm = float(patient_thickness_cm)
    dpr_in = float(dpr_in)

    if not all(math.isfinite(v) for v in (X, patient_thickness_cm, dpr_in)):
        raise ValueError("All measurements must be finite.")

    if patient_thickness_cm < 0 or dpr_in < 0:
        raise ValueError("Patient thickness and DPR cannot be negative.")

    source_to_skin_in = (
        float(sid_cm) - patient_thickness_cm
    ) / 2.54 - dpr_in

    if source_to_skin_in <= 0:
        raise ValueError("Source-to-skin distance must be positive.")

    ese = (
        float(R)
        * (float(kvp) / 100.0) ** X
        * float(mas)
        * ((100.0 / 2.54) / source_to_skin_in) ** 2
    )

    result = {
        "source_to_skin_in": source_to_skin_in,
        "ese_mr": ese,
    }

    if ese_limit_mr is not None:
        limit = float(ese_limit_mr)
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError("ESE limit must be positive.")

        result["ese_limit_mr"] = limit
        result["result"] = "Pass" if ese < limit else "FAIL"

    return result
