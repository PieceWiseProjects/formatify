"""Formatify - Auto-detect and standardize datetime formats from raw timestamps.

This package provides functionality to automatically detect and standardize
messy timestamp formats commonly found in log files, CSV data, and other
unstructured data sources.

Example:
    >>> from formatify_py import analyze_heterogeneous_timestamp_formats
    >>> samples = [
    ...     "2023-07-15T14:23:05Z",
    ...     "15/07/2023 14:23",
    ...     "Jul 15, 2023 02:23 PM",
    ...     "1689433385000"  # epoch in ms
    ... ]
    >>> results = analyze_heterogeneous_timestamp_formats(samples)
    >>> for gid, group in results.items():
    ...     print(f"Group {gid}: {group['format_string']}")
"""

from .exceptions import (
    FormatifyError,
    InconsistentFormatError,
    InsufficientDataError,
    TimestampParsingError,
    UnsupportedFormatError,
)
from .main import (
    analyze_heterogeneous_timestamp_formats,
    clean_timestamp,
    detect_iso_8601_features,
    group_timestamps_by_component_count,
    identify_format_groups,
    infer_datetime_format_from_samples,
    is_epoch,
    parse_timestamp,
)

__version__ = "1.0.2"
__author__ = "AR"
__email__ = "roy.aalekh@gmail.com"
__description__ = "Auto-detect and standardize datetime formats from raw timestamps"

__all__ = [
    # Main functions
    "analyze_heterogeneous_timestamp_formats",
    "infer_datetime_format_from_samples",
    "identify_format_groups",
    "group_timestamps_by_component_count",
    "detect_iso_8601_features",
    "is_epoch",
    "parse_timestamp",
    "clean_timestamp",
    # Exceptions
    "FormatifyError",
    "InconsistentFormatError",
    "InsufficientDataError",
    "TimestampParsingError",
    "UnsupportedFormatError",
]
