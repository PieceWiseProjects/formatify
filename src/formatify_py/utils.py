"""Utility functions for timestamp processing and analysis."""

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

from .constants import (
    COMMON_DELIMITERS,
    DATETIME_FORMAT_TO_USE_IN_RAW_TABLE,
    MAX_EPOCH_LENGTH,
    MAX_VALID_YEAR,
    MIN_EPOCH_LENGTH,
    MIN_VALID_YEAR,
    MONTH_REGEX_PATTERN,
    SEPARATOR_REGEX,
    TIMEZONE_REGEX,
)


def is_epoch(ts: str) -> bool:
    """Check if a timestamp string represents an epoch timestamp.

    Args:
        ts: The timestamp string to check.

    Returns:
        True if the string is a valid epoch timestamp (10-13 digits), False otherwise.

    Example:
        >>> is_epoch("1672531199")
        True
        >>> is_epoch("2023-01-01")
        False
    """
    return ts.isdigit() and MIN_EPOCH_LENGTH <= len(ts) <= MAX_EPOCH_LENGTH


def parse_timestamp(ts: str, fmt: str) -> Optional[str]:
    """Parse a timestamp string using the provided format.

    Handles both regular datetime formats and epoch timestamps.

    Args:
        ts: The timestamp string to parse.
        fmt: The format string to use for parsing (strftime format).

    Returns:
        Standardized timestamp string in YYYY-MM-DD HH:MM:SS format,
        or None if parsing fails.

    Example:
        >>> parse_timestamp("2023-01-01T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        '2023-01-01 12:00:00'
        >>> parse_timestamp("1672574400", "%s")
        '2023-01-01 12:00:00'
    """
    if is_epoch(ts):
        num = int(ts) / (1000 if len(ts) == 13 else 1)
        try:
            dt = datetime.fromtimestamp(num, tz=timezone.utc).replace(tzinfo=None)
            if MIN_VALID_YEAR <= dt.year <= MAX_VALID_YEAR:
                return dt.strftime(DATETIME_FORMAT_TO_USE_IN_RAW_TABLE)
        except (OSError, OverflowError, ValueError):
            return None

    try:
        dt = datetime.strptime(ts, fmt)
        return dt.replace(tzinfo=None).strftime(DATETIME_FORMAT_TO_USE_IN_RAW_TABLE)
    except ValueError:
        return None


def clean_timestamp(ts: str) -> str:
    """Clean a timestamp string by removing quotes and normalizing whitespace.

    Args:
        ts: The timestamp string to clean.

    Returns:
        Cleaned timestamp string with quotes removed and whitespace normalized.

    Example:
        >>> clean_timestamp("  '2023-01-01 12:00:00'  ")
        '2023-01-01 12:00:00'
    """
    return ts.strip().replace('"', "").replace("'", "").replace(r"\s+", " ")


def split_tokens_and_separators(ts: str) -> tuple[list[str], list[str]]:
    """Split a timestamp string into tokens and separators.

    Handles timezone detection and special cases like 'T' separator.

    Args:
        ts: The timestamp string to split.

    Returns:
        Tuple of (tokens, separators) where tokens are the meaningful parts
        and separators are the delimiters between them.

    Example:
        >>> tokens, seps = split_tokens_and_separators("2023-01-01T12:00:00Z")
        >>> tokens
        ['2023', '01', '01', '12', '00', '00', 'Z']
        >>> seps
        ['-', '-', 'T', ':', ':', '']
    """
    tz_match = TIMEZONE_REGEX.search(ts)
    tz = tz_match.group(1) if tz_match else None
    core = ts[: tz_match.start()] if tz_match else ts
    parts = re.split(r"(\d+|[A-Za-z]{2,})", core)
    tokens: list[str] = []
    seps: list[str] = []
    for i in range(1, len(parts), 2):
        tok, sep = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        if tok == "T":
            if seps:
                seps[-1] += tok + sep
            continue
        tokens.append(tok)
        seps.append(sep)
    if tz:
        tokens.append(tz)
        seps.append("")
    return tokens, seps


def split_timestamps_into_components(timestamps: list[str]) -> list[list[str]]:
    """Split multiple timestamps into their component parts.

    Args:
        timestamps: List of timestamp strings to split.

    Returns:
        List of component lists, one per timestamp.

    Example:
        >>> split_timestamps_into_components([
        ...     "2023-01-01 12:00:00", "2023-01-02 13:00:00"
        ... ])
        [['2023', '01', '01', '12', '00', '00'], ['2023', '01', '02', '13', '00', '00']]
    """
    result = []
    for ts in timestamps:
        tz_match = TIMEZONE_REGEX.search(ts)
        core = ts[: tz_match.start()] if tz_match else ts
        comps = SEPARATOR_REGEX.split(core)
        result.append(comps + ([tz_match.group(1)] if tz_match else []))
    return result


def calculate_component_change_frequencies(tokenized: list[list[str]]) -> list[int]:
    """Calculate how often each component position changes between timestamps.

    Args:
        tokenized: List of tokenized timestamps (each as list of components).

    Returns:
        List of change counts for each component position.

    Example:
        >>> tokens = [["2023", "01", "01"], ["2023", "01", "02"]]
        >>> calculate_component_change_frequencies(tokens)
        [0, 0, 1]
    """
    counts = [0] * len(tokenized[0])
    for prev, curr in zip(tokenized, tokenized[1:]):
        for i, (a, b) in enumerate(zip(prev, curr)):
            if a != b:
                counts[i] += 1
    return counts


def detect_iso_8601_features(timestamps: list[str]) -> dict[str, bool]:
    """Detect ISO 8601 features in a list of timestamps.

    Args:
        timestamps: List of timestamp strings to analyze.

    Returns:
        Dictionary with boolean flags for detected ISO 8601 features.

    Example:
        >>> detect_iso_8601_features(["2023-01-01T12:00:00Z"])
        {'time_separator': True, 'fractional_seconds': False, 'timezone_info': True}
    """
    return {
        "time_separator": any("T" in ts for ts in timestamps),
        "fractional_seconds": any(
            re.search(r":\d{2}\.\d{1,6}", ts) for ts in timestamps
        ),
        "timezone_info": any(TIMEZONE_REGEX.search(ts) for ts in timestamps),
    }


def identify_textual_month_positions(timestamps: list[str]) -> Optional[int]:
    """Identify the position of textual month names in timestamps.

    Args:
        timestamps: List of timestamp strings to analyze.

    Returns:
        The component index where textual months are most commonly found,
        or None if no textual months are detected.

    Example:
        >>> identify_textual_month_positions(["01-Jan-2023", "02-Feb-2023"])
        1
    """
    freq: defaultdict[int, int] = defaultdict(int)
    for ts in timestamps:
        for i, comp in enumerate(re.split(SEPARATOR_REGEX, ts)):
            if MONTH_REGEX_PATTERN.search(comp):
                freq[i] += 1
    return max(freq, key=lambda x: freq[x]) if freq else None


def identify_most_common_delimiter(timestamps: list[str]) -> str:
    """Identify the most commonly used delimiter in timestamps.

    Args:
        timestamps: List of timestamp strings to analyze.

    Returns:
        The most common delimiter character, defaults to "/" if none found.

    Example:
        >>> identify_most_common_delimiter(["2023-01-01", "2023-01-02"])
        '-'
    """
    freq = Counter(d for ts in timestamps for d in COMMON_DELIMITERS if d in ts)
    return freq.most_common(1)[0][0] if freq else "/"
