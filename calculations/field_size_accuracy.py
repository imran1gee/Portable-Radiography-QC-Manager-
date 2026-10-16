import math


def calculate_field_size_accuracy(
    measurement_distance,
    indicated_sid,
    selected_dimension,
    measured_dimension,
    tolerance_percent=2.0,
):
    values = [
        measurement_distance,
        indicated_sid,
        selected_dimension,
        measured_dimension,
    ]

    values = [float(value) for value in values]

    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ValueError("All distances and dimensions must be positive.")

    measurement_distance, indicated_sid, selected_dimension, measured_dimension = values

    error_percent = (
        (
            indicated_sid / measurement_distance
            * measured_dimension
            - selected_dimension
        )
        / indicated_sid
        * 100.0
    )

    passed = abs(error_percent) < tolerance_percent

    return {
        "error_percent": error_percent,
        "absolute_error_percent": abs(error_percent),
        "result": "Pass" if passed else "FAIL",
    }
