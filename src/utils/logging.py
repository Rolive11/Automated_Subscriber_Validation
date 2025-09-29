"""Utility functions for logging."""

from src.config.settings import DEBUG_MODE


def setup_logging():
    """Configure logging for the application."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )


def debug_print(message):
    """Print debug messages if DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        print(f"DEBUG: {message}")