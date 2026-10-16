
import statistics


def calculate_reproducibility(exposures):
    """Calculate mean, sample standard deviation, and CV."""

    values = [float(x) for x in exposures]

    if len(values) < 2:
        raise ValueError("At least two measurements are required.")

    if any(x <= 0 for x in values):
        raise ValueError("Exposure measurements must be positive.")

    mean = statistics.mean(values)
    std = statistics.stdev(values)
    cv = std / mean

    return {
        "mean": mean,
        "standard_deviation": std,
        "cv": cv
    }
