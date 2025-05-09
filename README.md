# formatify

[![PyPI version](https://img.shields.io/pypi/v/formatify.svg)](https://pypi.org/project/formatify) [![CI](https://github.com/PieceWiseProjects/formatify/actions/workflows/pr.yml/badge.svg)](https://github.com/PieceWiseProjects/formatify/actions) [![Release](https://github.com/PieceWiseProjects/formatify/actions/workflows/release.yml/badge.svg)](https://github.com/PieceWiseProjects/formatify/releases) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A small, zero-dependency library to infer and standardize datetime formats from a set of timestamp samples. Perfect for ETL pipelines, log parsing, and any situation where timestamp formats vary or aren’t known in advance.

---

## 📦 Installation

Using **pip**:

```bash
pip install formatify
```

Or with **uv**:

```bash
uv sync --locked
```

---

## 🚀 Quick Start

```python
from formatify.main import infer_datetime_format_from_samples

samples = [
    "2023-07-15T14:23:05Z",
    "2023-07-16T15:45:10Z",
    "2023-07-17T16:00:00Z",
]

result = infer_datetime_format_from_samples(samples)

print(result["format_string"])
# -> "%Y-%m-%dT%H:%M:%SZ"

print(result["standardized_timestamps"])
# -> ["2023-07-15 14:23:05", "2023-07-16 15:45:10", "2023-07-17 16:00:00"]
```

---

## 🔍 Features

* **Epoch detection**: Recognizes 10- or 13-digit UNIX timestamps.
* **Mixed formats**: Handles ISO 8601, textual months, custom delimiters, fractional seconds, and time-zones.
* **Automatic role assignment**: Infers which component is year/month/day/hour/minute/second.
* **Reconstruction**: Builds a proper `strftime` format string matching your data.
* **Standardization**: Converts all inputs to a uniform output format (configured in `app.constants`).
* **Heterogeneous handling**: Splits timestamp lists into groups by component count and analyzes each separately.

---

## 📖 API

### `infer_datetime_format_from_samples(samples: List[str], delimiter_hint: Optional[str] = None, separator_pattern: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]`

* **samples**: List of raw timestamp strings.
* **delimiter\_hint**: Force a primary delimiter (e.g., `/` or `-`).
* **separator\_pattern**: Provide exact separators from a representative sample.

**Returns** a dict with keys:

* `format_string`: the inferred `strftime` format.
* `component_roles`: map of component index → role (`year`, `month`, etc.).
* `change_frequencies`: how often each component changed across samples.
* `primary_delimiter`: the most common date separator.
* `iso_features`: flags for ISO traits (`time_separator`, `fractional_seconds`, `timezone_info`).
* `detected_timezone`: first seen timezone offset or `None`.
* `accuracy`: fraction of inputs that were successfully parsed.
* `standardized_timestamps`: list of normalized strings.

---

## 🛠 Development

```bash
# 1. Clone the repo
git clone git@github.com:YourOrg/formatify.git
cd formatify

# 2. Install uv and dependencies
uv install

# 3. Lint
uv run ruff src/formatify

# 4. Run tests
uv run pytest -q

# 5. Build distributions
python -m build
```

---

## 🤝 Contributing

1. Fork the repo and create a feature branch (`git checkout -b feature/foo`).
2. Commit your changes (`git commit -am "Add new feature"`).
3. Run lint & tests locally.
4. Push to the branch and open a Pull Request.

Please follow [Contributor Covenant](https://www.contributor-covenant.org) and our code style (See `.ruff.toml`).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
