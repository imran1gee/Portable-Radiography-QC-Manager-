
import math

from calculations.reproducibility import calculate_reproducibility
from calculations.linearity import calculate_linearity
from services.qc_data import get_qc_section, save_qc_data


def update_qc_results():
    measurements = get_qc_section("radiography_qc")
    results = {}

    if not measurements:
        save_qc_data("qc_results", results)
        return results

    # Four repeated exposure measurements
    exposures = [
        measurements.get(f"rep_exp{i}", 0)
        for i in range(1, 5)
    ]

    valid_reproducibility = all(
        isinstance(x, (int, float))
        and math.isfinite(x)
        and x > 0
        for x in exposures
    )

    if valid_reproducibility:
        results["reproducibility"] = (
            calculate_reproducibility(exposures)
        )

    # Four linearity settings:
    # The first uses the reproducibility mean.
    # The remaining three use separate exposure inputs.
    if "reproducibility" in results:
        mas_values = [
            measurements.get("mas4", 0),
            measurements.get("mas1", 0),
            measurements.get("mas2", 0),
            measurements.get("mas3", 0),
        ]

        linearity_exposures = [
            results["reproducibility"]["mean"],
            measurements.get("dose1", 0),
            measurements.get("dose2", 0),
            measurements.get("dose3", 0),
        ]

        values = mas_values + linearity_exposures

        if all(
            isinstance(x, (int, float))
            and math.isfinite(x)
            and x > 0
            for x in values
        ):
            results["linearity"] = calculate_linearity(
                linearity_exposures,
                mas_values,
            )

    save_qc_data("qc_results", results)
    return results
