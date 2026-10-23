"""Small in-memory rolling rate limiter."""
import time
def rate_limited(timestamps: list[float], max_calls: int = 10, window_seconds: float = 60.0,
                 now: float | None = None) -> bool:
    if max_calls < 1 or window_seconds <= 0:
        raise ValueError("max_calls and window_seconds must be positive")
    current = time.time() if now is None else float(now)
    timestamps[:] = [t for t in timestamps if current - t <= window_seconds]
    if len(timestamps) >= max_calls:
        return True
    timestamps.append(current)
    return False
