"""Constants and patterns used throughout the formatify package."""

import re

# Common delimiters found in timestamps
COMMON_DELIMITERS = ["/", "-", ".", " ", ","]

# Month abbreviations (3-letter)
MONTH_ABBREVIATIONS = {
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
}

# Full month names
MONTH_FULL_NAMES = {
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
}

# Compiled regex pattern for matching month names (both full and abbreviated)
MONTH_REGEX_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(sorted(MONTH_ABBREVIATIONS | MONTH_FULL_NAMES, key=len, reverse=True))
    + r")\b"
)

# Regex for splitting timestamps into components (matches separators)
SEPARATOR_REGEX = re.compile(r"[\sT:/\-.]+")

# Regex for detecting timezone information at the end of timestamps
TIMEZONE_REGEX = re.compile(r"([+-]\d{2}:?\d{2}|Z)$")

# Standard datetime format used for normalized output
DATETIME_FORMAT_TO_USE_IN_RAW_TABLE = "%Y-%m-%d %H:%M:%S"

# Valid year range for epoch validation
MIN_VALID_YEAR = 1970
MAX_VALID_YEAR = 2100

# Epoch timestamp length constraints
MIN_EPOCH_LENGTH = 10  # 10 digits for seconds since epoch
MAX_EPOCH_LENGTH = 13  # 13 digits for milliseconds since epoch

# Component role names
COMPONENT_ROLES = {
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
    "microsecond",
    "millisecond",
    "timezone",
}

# Default separators for different datetime components
DEFAULT_DATE_DELIMITER = "/"
DEFAULT_TIME_DELIMITER = ":"
ISO_TIME_SEPARATOR = "T"
