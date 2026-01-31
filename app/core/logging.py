import logging
import sys

def setup_logging() -> None:
    """
    Centralized logging config.
    Why: AI apps need strong observability (latency, errors, tool calls later).
    """
    logging.basicConfig(
        level = logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )