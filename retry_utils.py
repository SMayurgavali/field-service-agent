import time


def run_with_retries(
    operation,
    max_attempts=3,
    on_retry=None,
    sleep_fn=None,
):
    """Retry an operation only for temporary API errors."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    sleep = sleep_fn or time.sleep

    retryable_errors = (
        "503",
        "429",
        "500",
        "502",
        "504",
        "unavailable",
        "resource_exhausted",
        "timed out",
        "timeout",
    )

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except Exception as exc:
            error_text = str(exc).lower()

            should_retry = any(
                message in error_text
                for message in retryable_errors
            )

            if not should_retry or attempt == max_attempts:
                raise

            wait_seconds = attempt * 2

            if on_retry:
                on_retry(
                    attempt + 1,
                    max_attempts,
                    wait_seconds,
                    exc,
                )

            sleep(wait_seconds)

    raise RuntimeError("Workflow failed after retries.")