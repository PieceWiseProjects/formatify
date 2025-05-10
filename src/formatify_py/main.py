import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import permutations
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

COMMON_DELIMITERS = ["/", "-", ".", " ", ","]
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
MONTH_REGEX_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(sorted(MONTH_ABBREVIATIONS | MONTH_FULL_NAMES, key=len, reverse=True))
    + r")\b"
)
SEPARATOR_REGEX = re.compile(r"[\sT:/\-.]+")
TIMEZONE_REGEX = re.compile(r"([+-]\d{2}:?\d{2}|Z)$")
DATETIME_FORMAT_TO_USE_IN_RAW_TABLE = "%Y-%m-%d %H:%M:%S"

def is_epoch(ts: str) -> bool:
    return ts.isdigit() and 10 <= len(ts) <= 13


def parse_timestamp(ts: str, fmt: str) -> Optional[str]:
    if is_epoch(ts):
        num = int(ts) / (1000 if len(ts) == 13 else 1)
        try:
            dt = datetime.fromtimestamp(num, tz=timezone.utc).replace(tzinfo=None)
            if 1970 <= dt.year <= 2100:
                return dt.strftime(DATETIME_FORMAT_TO_USE_IN_RAW_TABLE)
        except (OSError, OverflowError, ValueError):
            return None

    try:
        dt = datetime.strptime(ts, fmt)
        return dt.replace(tzinfo=None).strftime(DATETIME_FORMAT_TO_USE_IN_RAW_TABLE)
    except ValueError:
        return None


def clean_timestamp(ts: str) -> str:
    return ts.strip().replace('"', "").replace("'", "").replace("\s+", " ")


def split_tokens_and_separators(ts: str) -> Tuple[List[str], List[str]]:
    tz_match = TIMEZONE_REGEX.search(ts)
    tz = tz_match.group(1) if tz_match else None
    core = ts[: tz_match.start()] if tz_match else ts
    parts = re.split(r"(\d+|[A-Za-z]{2,})", core)
    tokens, seps = [], []
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


def split_timestamps_into_components(timestamps: List[str]) -> List[List[str]]:
    result = []
    for ts in timestamps:
        tz_match = TIMEZONE_REGEX.search(ts)
        core = ts[: tz_match.start()] if tz_match else ts
        comps = SEPARATOR_REGEX.split(core)
        result.append(comps + ([tz_match.group(1)] if tz_match else []))
    return result


def calculate_component_change_frequencies(tokenized: List[List[str]]) -> List[int]:
    counts = [0] * len(tokenized[0])
    for prev, curr in zip(tokenized, tokenized[1:]):
        for i, (a, b) in enumerate(zip(prev, curr)):
            if a != b:
                counts[i] += 1
    return counts


def detect_iso_8601_features(timestamps: List[str]) -> Dict[str, bool]:
    return {
        "time_separator": any("T" in ts for ts in timestamps),
        "fractional_seconds": any(
            re.search(r":\d{2}\.\d{1,6}", ts) for ts in timestamps
        ),
        "timezone_info": any(TIMEZONE_REGEX.search(ts) for ts in timestamps),
    }


def identify_textual_month_positions(timestamps: List[str]) -> Optional[int]:
    freq: DefaultDict[int, int] = defaultdict(int)
    for ts in timestamps:
        for i, comp in enumerate(re.split(SEPARATOR_REGEX, ts)):
            if MONTH_REGEX_PATTERN.search(comp):
                freq[i] += 1
    return max(freq, key=freq.get) if freq else None


def determine_component_roles(
    freqs: List[int], tokenized: List[List[str]], timestamps: List[str]
) -> Dict[int, str]:
    current_year = datetime.now().year
    roles: Dict[int, str] = {}

    def get_col(idx: int) -> List[str]:
        return [row[idx] for row in tokenized]

    def valid_year(vals: List[str]) -> bool:
        try:
            years = [int(v) for v in vals]
            return all(0 <= y <= 99 or 1900 <= y <= current_year + 1 for y in years)
        except ValueError:
            return False

    def valid_day(vals: List[str]) -> bool:
        try:
            return all(1 <= int(re.sub(r"\D", "", v)) <= 31 for v in vals if v)
        except ValueError:
            return False

    def valid_hour(vals: List[str]) -> bool:
        try:
            return all(0 <= int(v) <= 23 for v in vals)
        except ValueError:
            return False

    def valid_min_sec(vals: List[str]) -> bool:
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
    if "year" in roles:
        if "month" in roles and date_idxs:
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
            best, combo = -1, None
            for y, d in permutations(date_idxs, 2):
                if valid_year(get_col(y)) and valid_day(get_col(d)):
                    y_rate = freqs[y] / len(tokenized)
                    d_rate = freqs[d] / len(tokenized)
                    score = 3 if y_rate < 0.05 else 1 if y_rate < 0.1 else 0
                    score += 2 if d_rate > 0.9 else 1 if d_rate > 0.5 else 0
                    score += (d_rate - y_rate) * 10
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
    roles: Dict[int, str],
    tokenized: List[List[str]],
    date_delim: str = "/",
    time_delim: str = ":",
    iso_feats: Optional[Dict[str, bool]] = None,
    separators: Optional[List[str]] = None,
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
        sep = "T" if iso_feats.get("time_separator") else " "
        fmt += sep + time_delim.join(time_parts)
        if iso_feats.get("fractional_seconds"):
            fmt += ".%f"
        if iso_feats.get("timezone_info"):
            fmt += "%z"
    return fmt


def identify_most_common_delimiter(timestamps: List[str]) -> str:
    freq = Counter(d for ts in timestamps for d in COMMON_DELIMITERS if d in ts)
    return freq.most_common(1)[0][0] if freq else "/"


def infer_datetime_format_from_samples(
    timestamps: List[str],
    delimiter_hint: Optional[str] = None,
    separator_pattern: Optional[Tuple[str, ...]] = None,
) -> Dict[str, Any]:
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
    if len({len(t) for t in tokenized}) != 1:
        raise ValueError("Inconsistent component counts.")

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
            time_delim=":",
            iso_feats=iso_feats,
            separators=seps,
        )
    else:
        fmt = generate_format_string_from_components(
            roles, tokenized, date_delim=hint, time_delim=":", iso_feats=iso_feats
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


def group_timestamps_by_component_count(timestamps: List[str]) -> Dict[int, List[str]]:
    groups: DefaultDict[int, List[str]] = defaultdict(list)
    for ts in timestamps:
        count = len(SEPARATOR_REGEX.split(clean_timestamp(ts)))
        groups[count].append(clean_timestamp(ts))
    return dict(groups)


def identify_format_groups(
    timestamps: List[str],
) -> Dict[int, Tuple[List[str], Dict[str, Any]]]:
    grouped = group_timestamps_by_component_count(timestamps)
    result, gid = {}, 0
    for samples in grouped.values():
        buckets: DefaultDict[Tuple, List[str]] = defaultdict(list)
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
    timestamps: List[str], delimiter_hint: Optional[str] = None
) -> Dict[int, Dict[str, Any]]:
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
    results: Dict[int, Dict[str, Any]] = {}
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
