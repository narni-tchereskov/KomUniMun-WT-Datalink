from time import perf_counter


def get_elapsed(reference_time: float, precision: int = 3) -> float:
    """
    Function responsible for returning formatted total elapsed time.

    Args:
        reference_time (float): Initial reference time during execution.
        precision (int): Quantity of decimal places.

    Returns:
        Time elapsed since the reference time value.
    """

    return round(perf_counter() - reference_time, precision)
