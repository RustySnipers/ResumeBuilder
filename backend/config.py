import os


def is_lite_mode() -> bool:
    """Return True when Lite Mode is enabled via the ``LITE_MODE`` flag."""

    value = os.getenv("LITE_MODE", "false")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
