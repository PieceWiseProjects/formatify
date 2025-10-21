import logging
import re
from collections import defaultdict
from datetime import datetime
from itertools import permutations
from typing import Any, Optional

from .constants import (
    DEFAULT_DATE_DELIMITER,
    DEFAULT_TIME_DELIMITER,
    ISO_TIME_SEPARATOR,
    MONTH_REGEX_PATTERN,
    SEPARATOR_REGEX,
    TIMEZONE_REGEX,
)
from .exceptions import (
    InconsistentFormatError,
    InsufficientDataError,
)
from .utils import (
    calculate_component_change_frequencies,
    clean_timestamp,
    detect_iso_8601_features,
    identify_most_common_delimiter,
    identify_textual_month_positions,
    is_epoch,
    parse_timestamp,
    split_timestamps_into_components,
    split_tokens_and_separators,
)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def determine_component_roles(
    freqs: list[int], tokenized: list[list[str]], timestamps: list[str]
) -> dict[int, str]:
    current_year = datetime.now().year
    roles: dict[int, str] = {}

    def get_col(idx: int) -> list[str]:
        return [row[idx] for row in tokenized]

    def valid_year(vals: list[str]) -> bool:
        try:
            years = [int(v) for v in vals]
            return all(0 <= y <= 99 or 1900 <= y <= current_year + 1 for y in years)
        except ValueError:
            return False

    def valid_day(vals: list[str]) -> bool:
        try:
            return all(1 <= int(re.sub(r"\D", "", v)) <= 31 for v in vals if v)
        except ValueError:
            return False

    def valid_hour(vals: list[str]) -> bool:
        try:
            return all(0 <= int(v) <= 23 for v in vals)
        except ValueError:
            return False

    def valid_min_sec(vals: list[str]) -> bool:
        try:
            nums = [int(v) for v in vals]
            return all(0 <= n <= 59 for n in nums)
        except ValueError:
            return False

    month_idx = identify_textual_month_positions(timestamps)
    if month_idx is not None:
        roles[month_idx] = "month"

    n = len(freqs)
    date_idxs = [i for i in range(3) if i != month_idx]
    time_idxs = list(range(3, n)) if n <= 6 else list(range(3, n - 1))

    # Year by 4-digit
    four_digit = [
        i for i in date_idxs if all(v.isdigit() and len(v) == 4 for v in get_col(i))
    ]
    if four_digit:
        roles[four_digit[0]] = "year"
        date_idxs.remove(four_digit[0])

    # Month fallback
    month_cands = [
        i
        for i in date_idxs
        if all(v.isdigit() and 1 <= int(v) <= 12 for v in get_col(i))
    ]
    if month_cands:
        m = min(month_cands, key=lambda i: freqs[i])
        roles[m] = "month"
        date_idxs.remove(m)

    # Day/year fallback
    if "year" in roles.values():
        if "month" in roles.values() and date_idxs:
            roles[date_idxs[0]] = "day"
        elif len(date_idxs) > 1:
            d = max(date_idxs, key=lambda i: freqs[i])
            roles[d] = "day"
            date_idxs.remove(d)
            roles[date_idxs[0]] = "month"
        elif date_idxs:
            roles[date_idxs[0]] = "month"
    else:
        if len(date_idxs) == 1:
            roles[date_idxs[0]] = "day"
        elif len(date_idxs) > 1:
            best: float = -1.0
            combo: Optional[tuple[int, int]] = None
            for y, d in permutations(date_idxs, 2):
                if valid_year(get_col(y)) and valid_day(get_col(d)):
                    y_rate = freqs[y] / len(tokenized)
                    d_rate = freqs[d] / len(tokenized)
                    score: float = (
                        3.0 if y_rate < 0.05 else 1.0 if y_rate < 0.1 else 0.0
                    )
                    score += 2.0 if d_rate > 0.9 else 1.0 if d_rate > 0.5 else 0.0
                    score += (d_rate - y_rate) * 10.0
                    if score > best:
                        best, combo = score, (y, d)
            if combo:
                roles[combo[0]] = "year"
                roles[combo[1]] = "day"
                left = [i for i in range(3) if i not in combo]
                if left:
                    roles[left[0]] = "month"

    # Time components
    for name, idx in zip(["hour", "minute", "second"], time_idxs):
        vals = get_col(idx)
        if name == "minute" and all(v == "00" for v in vals):
            roles[idx] = "minute"
        elif (name == "hour" and valid_hour(vals)) or valid_min_sec(vals):
            roles[idx] = name

    iso = detect_iso_8601_features(timestamps)
    last = get_col(n - 1)
    if iso["fractional_seconds"]:
        lengths = {len(v) for v in last if v}
        if len(lengths) == 1:
            roles[n - 1] = "millisecond" if lengths.pop() == 3 else "microsecond"
    if iso["timezone_info"] and any(TIMEZONE_REGEX.fullmatch(v) for v in last):
        roles[n - 1] = "timezone"

    return roles


def generate_format_string_from_components(
    roles: dict[int, str],
    tokenized: list[list[str]],
    date_delim: str = DEFAULT_DATE_DELIMITER,
    time_delim: str = DEFAULT_TIME_DELIMITER,
    iso_feats: Optional[dict[str, bool]] = None,
    separators: Optional[list[str]] = None,
) -> str:
    iso_feats = iso_feats or {}
    directives = {
        "year": lambda x: "%Y" if len(x) == 4 else "%y",
        "month": lambda x: (
            "%b" if x.isalpha() and len(x) == 3 else "%B" if x.isalpha() else "%m"
        ),
        "day": lambda x: "%d",
        "hour": lambda x: "%H",
        "minute": lambda x: "%M",
        "second": lambda x: "%S",
        "microsecond": lambda x: "%f",
        "timezone": lambda x: "%z",
    }

    if separators:
        first = tokenized[0]
        parts = []
        for i, tok in enumerate(first):
            role = roles.get(i)
            part = directives[role](tok) if role else tok
            parts.append(part)
            sep = separators[i]
            if sep in ("+", "-") and roles.get(i + 1) == "timezone":
                continue
            if sep:
                parts.append(sep)
        return "".join(parts)

    sorted_roles = sorted(roles.items())
    date_parts = [
        directives[r](tokenized[0][i])
        for i, r in sorted_roles
        if r in ("year", "month", "day")
    ]
    fmt = date_delim.join(date_parts)
    time_parts = [
        directives[r](tokenized[0][i])
        for i, r in sorted_roles
        if r in ("hour", "minute", "second")
    ]
    if time_parts:
        sep = ISO_TIME_SEPARATOR if iso_feats.get("time_separator") else " "
        fmt += sep + time_delim.join(time_parts)
        if iso_feats.get("fractional_seconds"):
            fmt += ".%f"
        if iso_feats.get("timezone_info"):
            fmt += "%z"
    return fmt


def infer_datetime_format_from_samples(
    timestamps: list[str],
    delimiter_hint: Optional[str] = None,
    separator_pattern: Optional[tuple[str, ...]] = None,
) -> dict[str, Any]:
    """Infer datetime format from samples with consistent structure.

    This function analyzes timestamps that are assumed to have the same format
    and infers the appropriate strftime format string.

    Args:
        timestamps: List of timestamp strings with consistent format.
        delimiter_hint: Optional hint for the primary delimiter.
        separator_pattern: Optional tuple of separator patterns.

    Returns:
        Dictionary containing:
        - format_string: Inferred strftime format string
        - component_roles: Mapping of component indices to roles
        - change_frequencies: Variability of each component
        - primary_delimiter: Primary delimiter used
        - iso_features: Detected ISO 8601 features
        - detected_timezone: Detected timezone if present
        - accuracy: Fraction of successfully parsed timestamps
        - standardized_timestamps: List of normalized timestamps

    Raises:
        ValueError: If timestamps have inconsistent component counts.

    Example:
        >>> samples = ["2023-07-15T14:23:05Z", "2023-07-16T15:24:06Z"]
        >>> result = infer_datetime_format_from_samples(samples)
        >>> result['format_string']
        '%Y-%m-%dT%H:%M:%SZ'
    """
    if all(is_epoch(ts) for ts in timestamps):
        std = [parse_timestamp(ts, "%s") for ts in timestamps]
        return {
            "format_string": "%s",
            "component_roles": {},
            "change_frequencies": [],
            "primary_delimiter": None,
            "iso_features": {},
            "accuracy": sum(1 for t in std if t) / len(std),
            "standardized_timestamps": std,
        }

    cleaned = [clean_timestamp(ts) for ts in timestamps]
    tokenized = split_timestamps_into_components(cleaned)
    component_counts = {len(t) for t in tokenized}
    if len(component_counts) != 1:
        raise InconsistentFormatError(component_counts)

    hint = delimiter_hint or identify_most_common_delimiter(cleaned)
    freqs = calculate_component_change_frequencies(tokenized)
    roles = determine_component_roles(freqs, tokenized, timestamps)
    iso_feats = detect_iso_8601_features(timestamps)
    tz_list = [m.group(1) for ts in timestamps if (m := TIMEZONE_REGEX.search(ts))]
    tz = tz_list[0] if tz_list else None

    if separator_pattern:
        toks, seps = split_tokens_and_separators(cleaned[0])
        fmt = generate_format_string_from_components(
            roles,
            [toks],
            date_delim=hint,
            time_delim=DEFAULT_TIME_DELIMITER,
            iso_feats=iso_feats,
            separators=seps,
        )
    else:
        fmt = generate_format_string_from_components(
            roles,
            tokenized,
            date_delim=hint,
            time_delim=DEFAULT_TIME_DELIMITER,
            iso_feats=iso_feats,
        )

    std = [parse_timestamp(ts, fmt) for ts in cleaned]
    return {
        "format_string": fmt,
        "component_roles": roles,
        "change_frequencies": freqs,
        "primary_delimiter": hint,
        "iso_features": iso_feats,
        "detected_timezone": tz,
        "accuracy": sum(1 for t in std if t) / len(std),
        "standardized_timestamps": std,
    }


def group_timestamps_by_component_count(timestamps: list[str]) -> dict[int, list[str]]:
    groups: defaultdict[int, list[str]] = defaultdict(list)
    for ts in timestamps:
        count = len(SEPARATOR_REGEX.split(clean_timestamp(ts)))
        groups[count].append(clean_timestamp(ts))
    return dict(groups)


def identify_format_groups(
    timestamps: list[str],
) -> dict[int, tuple[list[str], dict[str, Any]]]:
    grouped = group_timestamps_by_component_count(timestamps)
    result, gid = {}, 0
    for samples in grouped.values():
        buckets: defaultdict[tuple, list[str]] = defaultdict(list)
        for ts in samples:
            toks, seps = split_tokens_and_separators(ts)
            feats = {
                "has_T": "T" in ts,
                "has_timezone": bool(TIMEZONE_REGEX.search(ts)),
                "has_text_month": bool(MONTH_REGEX_PATTERN.search(ts)),
                "sep_pattern": tuple(seps),
            }
            buckets[tuple(sorted(feats.items()))].append(ts)
        for feats_key, grp in buckets.items():
            result[gid] = (grp, dict(feats_key))
            gid += 1
    return result


def analyze_heterogeneous_timestamp_formats(
    timestamps: list[str], delimiter_hint: Optional[str] = None
) -> dict[int, dict[str, Any]]:
    """Analyze and standardize heterogeneous timestamp formats.

    This is the main entry point for the formatify library. It takes a list of
    timestamp strings that may be in different formats and automatically groups
    them by format, infers the format string for each group, and returns
    standardized timestamps.

    Args:
        timestamps: List of timestamp strings to analyze.
        delimiter_hint: Optional hint for the primary delimiter to use.

    Returns:
        Dictionary mapping group IDs to analysis results. Each result contains:
        - format_string: Inferred strftime format string
        - standardized_timestamps: List of normalized timestamp strings
        - component_roles: Mapping of component indices to their roles
        - change_frequencies: How often each component changes
        - iso_features: Detected ISO 8601 features
        - detected_timezone: Detected timezone if present
        - accuracy: Fraction of successfully parsed timestamps
        - coverage: Fraction of input timestamps in this group
        - samples: Original timestamps in this group
        - group_features: Detected structural features

    Raises:
        InsufficientDataError: If no timestamps are provided.
        InconsistentFormatError: If timestamps have inconsistent component counts
            within a group.
        FormatifyError: For other analysis errors.

    Example:
        >>> samples = [
        ...     "2023-07-15T14:23:05Z",
        ...     "15/07/2023 14:23",
        ...     "Jul 15, 2023 02:23 PM",
        ...     "1689433385000"  # epoch in ms
        ... ]
        >>> results = analyze_heterogeneous_timestamp_formats(samples)
        >>> for gid, group in results.items():
        ...     print(f"Group {gid}: {group['format_string']}")
        Group 0: %Y-%m-%dT%H:%M:%SZ
        Group 1: %d/%m/%Y %H:%M
        Group 2: %b %d, %Y %I:%M %p
        Group 3: %s
    """
    if not timestamps:
        raise InsufficientDataError(0, 1, "No timestamps provided for analysis")

    logger.info(f"Analyzing {len(timestamps)} timestamps for format detection")

    if all(is_epoch(ts) for ts in timestamps):
        std = [parse_timestamp(ts, "%s") for ts in timestamps]
        return {
            0: {
                "format_string": "%s",
                "component_roles": {},
                "change_frequencies": [],
                "primary_delimiter": None,
                "iso_features": {},
                "accuracy": sum(1 for t in std if t) / len(std),
                "standardized_timestamps": std,
            }
        }

    groups = identify_format_groups(timestamps)
    results: dict[int, dict[str, Any]] = {}
    for gid, (samples, feats) in groups.items():
        try:
            analysis = infer_datetime_format_from_samples(
                samples, delimiter_hint, feats.get("sep_pattern")
            )
            analysis.update(
                {
                    "samples": samples,
                    "coverage": len(samples) / len(timestamps),
                    "group_features": feats,
                }
            )
        except Exception as e:
            analysis = {
                "error": str(e),
                "samples": samples,
                "coverage": len(samples) / len(timestamps),
                "group_features": feats,
            }
        results[gid] = analysis
    return results
