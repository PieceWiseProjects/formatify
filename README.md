# formatify

---

> Auto-detect and standardize messy timestamp formats.
> Perfect for log parsers, data pipelines, or anyone tired of wrestling with inconsistent datetime strings.

[![PyPI version](https://img.shields.io/pypi/v/formatify_py.svg)](https://pypi.org/project/formatify_py)
[![CI](https://github.com/PieceWiseProjects/formatify/actions/workflows/pr.yml/badge.svg)](https://github.com/PieceWiseProjects/formatify/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[![Downloads](https://static.pepy.tech/badge/formatify_py)](https://pepy.tech/project/formatify_py)
![Python](https://img.shields.io/pypi/pyversions/formatify_py)
![Platform](https://img.shields.io/badge/platform-cross--platform-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

---

![Demo of formatify in action](Animation.gif)

---

## Problem

Ever pulled in a CSV or log file and found timestamps like this?

```plaintext
2023-03-01T12:30:45Z, 01/03/2023 12:30, Mar 1 2023 12:30 PM
```

How do you reliably infer and **standardize** them — especially when:

* formats are mixed?
* you have no schema?
* fractional seconds and timezones are involved?

---

## Solution

`formatify` infers the datetime format(s) from a list of timestamp strings and gives you:

* a valid `strftime` format string per group,
* component roles (e.g. year, month, day),
* clean, standardized timestamps,
* structural grouping when needed.

No dependencies. Works out of the box.

---

## What This Library Does

Behind the scenes, `formatify` uses:

* **Regex patterns** to split and identify timestamp tokens
* **Heuristics** to assign roles like `year`, `month`, `hour`, etc.
* **Frequency analysis** to distinguish stable vs. changing components
* **ISO 8601 detection** for timezones, 'T' separators, and fractional seconds
* **Smart fallbacks** for missing delimiters or ambiguous parts
* **Epoch detection** (10 or 13 digit UNIX timestamps)

It produces:

* one or more `%Y-%m-%dT%H:%M:%SZ`-style format strings
* lists of cleaned, standardized `YYYY-MM-DD HH:MM:SS` values
* per-group accuracy and metadata

---

## Quick Example

```python
from formatify_py import analyze_heterogeneous_timestamp_formats

samples = [
    "2023-07-15T14:23:05Z",
    "15/07/2023 14:23",
    "Jul 15, 2023 02:23 PM",
    "1689433385000"  # epoch in ms
]

results = analyze_heterogeneous_timestamp_formats(samples)

for gid, group in results.items():
    print("Group", gid)
    print("→ Format:", group["format_string"])
    print("→ Standardized:", group["standardized_timestamps"][:2])
```

---

## Features

- Auto-detect `strftime` format
- Handles ISO 8601, text months, UNIX epoch
- Infers year/month/day/hour/minute roles
- Groups mixed formats automatically
- Timezone-aware
- No dependencies
- Fast and customizable

---

## API

### Main Entry Point

```python
analyze_heterogeneous_timestamp_formats(samples: List[str]) -> Dict[int, Dict[str, Any]]
```

Returns a dictionary mapping group IDs to result dictionaries. Each result includes:

* `format_string`: inferred `strftime` string
* `standardized_timestamps`: parsed & normalized strings
* `component_roles`: index → role
* `change_frequencies`: component variability
* `iso_features`: flags for ISO 8601 traits
* `detected_timezone`: parsed offset (if any)
* `coverage`: fraction of total samples in this group
* `accuracy`: percent of valid parses in group
* `primary_delimiter`: most common delimiter used
* `samples`: original timestamps in this group
* `group_features`: detected structural features

### Lower-Level Functions

If you know all your samples have the same format:

```python
infer_datetime_format_from_samples(samples: List[str]) -> Dict[str, Any]
```

---

## Mixed Format Handling

`formatify` is designed to handle **real-world timestamp mess**. When your input includes a mix of styles — ISO, slashed, text-months, or epoch — it:

1. **Groups samples** by structural similarity
2. **Infers format** per group
3. **Standardizes timestamps** across each group

This lets you feed in 3 formats or 30, and still get clean, grouped results.

---

## Design Notes

Want to know how the internals work? Check out:

* [How Formatify Thinks About Timestamps](docs/design.md)

---

## Dev Guide

```bash
# Clone the repo
git clone https://github.com/PieceWiseProjects/formatify.git
cd formatify

# Set up environment
uv pip install -e .[dev,test]

# Lint and format
uv run ruff src/formatify_py

# Run tests
uv run pytest --cov=src/formatify_py

# Build for release
uv run python -m build
```

---

## Contributing

We're just getting started — contributions, issues, and ideas welcome!

1. Fork and branch: `git checkout -b feature/my-feature`
2. Code and test
3. Lint and push
4. Open a pull request

Follow our [Contributor Guidelines](https://www.contributor-covenant.org).

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Credits

Built and maintained by [Aalekh Roy](https://github.com/RoyAalekh)
Part of the [PieceWiseProjects](https://github.com/PieceWiseProjects) initiative.
