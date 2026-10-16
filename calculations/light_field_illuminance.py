import math


def calculate_light_field_illuminance(
    q1_lux,
    q2_lux,
    q3_lux,
    q4_lux,
    background_lux,
):
    values = [q1_lux, q2_lux, q3_lux, q4_lux, background_lux]

    try:
        values = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter valid illuminance measurements.") from exc

    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ValueError("Illuminance measurements must be finite and nonnegative.")

    q1, q2, q3, q4, background = values

    average = (q1 + q2 + q3 + q4) / 4
    corrected_average = average - background

    return {
        "average_lux": average,
        "background_lux": background,
        "corrected_average_lux": corrected_average,
        "state_result": "Pass" if corrected_average >= 100 else "FAIL",
        "federal_result": "Pass" if corrected_average >= 160 else "FAIL",
    }
