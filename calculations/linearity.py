
import math


def calculate_linearity(exposures, mas_values):
    """
    Calculate tube output linearity using the Excel QC
    workbook's maximum-versus-minimum method.

    CL = (maximum output - minimum output) /
         (maximum output + minimum output)
    """

    if len(exposures) != len(mas_values):
        raise ValueError(
            "Exposure and mAs measurements must match."
        )

    if len(exposures) < 2:
        raise ValueError(
            "At least two measurements are required."
        )

    exposures = [float(x) for x in exposures]
    mas_values = [float(x) for x in mas_values]

    if any(
        not math.isfinite(x) or x <= 0
        for x in exposures + mas_values
    ):
        raise ValueError(
            "All exposure and mAs values must be finite and positive."
        )

    outputs = [
        exposure / mas
        for exposure, mas in zip(exposures, mas_values)
    ]

    maximum_output = max(outputs)
    minimum_output = min(outputs)

    coefficient = (
        (maximum_output - minimum_output)
        / (maximum_output + minimum_output)
    )

    return {
        "normalized_outputs": outputs,
        "linearity_coefficients": [
            abs(outputs[i] - outputs[i + 1])
            / (outputs[i] + outputs[i + 1])
            for i in range(len(outputs) - 1)
        ],
        "maximum_linearity_coefficient": coefficient,
        "maximum_output": maximum_output,
        "minimum_output": minimum_output
    }
