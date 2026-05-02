from contextlib import contextmanager
from time import perf_counter


@contextmanager
def profiler(name: str, precision: int = 3):
    """Function responsible for profiling blocks of code.

    Args:
        name (str): Name assigned to the code block.
        precision (int): Decimal precision of the profiling dictionary.

    Yields:
        Dictionary with name as key and execution time as value.
    """

    result: dict[str, float] = {}
    start_time = perf_counter()

    try:
        yield result

    finally:
        end_time = perf_counter()
        duration = end_time - start_time

        result[name] = round(duration, precision)
