"""Default configuration for mermaidgen."""

import os

DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
DEFAULT_MMDC_BINARY = "mmdc"
DEFAULT_FORMAT = "png"
SUBPROCESS_TIMEOUT = 30  # seconds
SUPPORTED_FORMATS = ("png", "svg", "pdf")
