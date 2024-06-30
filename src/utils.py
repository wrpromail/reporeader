import functools
import time

def measure_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        function_time_ms = (end_time - start_time) * 1000
        print(f"Function {func.__name__} took {function_time_ms:.2f} milliseconds to execute.")
        return result
    return wrapper
