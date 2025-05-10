from formatify_py.main import (
    is_epoch,
    parse_timestamp,
    clean_timestamp,
    split_tokens_and_separators,
    split_timestamps_into_components,
    calculate_component_change_frequencies,
    detect_iso_8601_features,
    identify_textual_month_positions,
    determine_component_roles,
    generate_format_string_from_components,
    identify_most_common_delimiter,
    infer_datetime_format_from_samples,
    group_timestamps_by_component_count,
    identify_format_groups,
    analyze_heterogeneous_timestamp_formats,
)


def test_is_epoch():
    assert is_epoch("1672531199")
    assert is_epoch("1672531199123")
    assert not is_epoch("2023-07-15")


def test_parse_timestamp_epoch():
    ts = "1672531199"
    assert parse_timestamp(ts, "%s") == "2022-12-31 23:59:59"


def test_clean_timestamp():
    assert clean_timestamp(" '2023-01-01 12:00:00' ") == "2023-01-01 12:00:00"


def test_split_tokens_and_separators():
    tokens, seps = split_tokens_and_separators("2023-01-01T12:00:00Z")
    assert tokens[-1] == "Z"
    assert "T" not in tokens


def test_split_timestamps_into_components():
    ts = ["2023-01-01 12:00:00", "2023-01-02 13:00:00"]
    comps = split_timestamps_into_components(ts)
    assert comps[0][0] == "2023"


def test_calculate_component_change_frequencies():
    tokens = [["2023", "01", "01"], ["2023", "01", "02"]]
    freqs = calculate_component_change_frequencies(tokens)
    assert freqs == [0, 0, 1]


def test_detect_iso_8601_features():
    features = detect_iso_8601_features(["2023-01-01T12:00:00Z"])
    assert features["time_separator"]
    assert not features["fractional_seconds"]


def test_identify_textual_month_positions():
    pos = identify_textual_month_positions(["01-Jan-2023", "02-Feb-2023"])
    assert pos == 1


def test_determine_component_roles_simple():
    timestamps = ["2023-01-01 12:00:00", "2023-01-02 13:00:00"]
    tokenized = split_timestamps_into_components(timestamps)
    freqs = calculate_component_change_frequencies(tokenized)
    roles = determine_component_roles(freqs, tokenized, timestamps)
    assert "year" in roles.values()
    assert "month" in roles.values()
    assert "day" in roles.values()


def test_generate_format_string_from_components():
    tokens = [["2023", "01", "01", "12", "00", "00"]]
    roles = {0: "year", 1: "month", 2: "day", 3: "hour", 4: "minute", 5: "second"}
    fmt = generate_format_string_from_components(roles, tokens)
    assert fmt.startswith("%Y")


def test_identify_most_common_delimiter():
    ts = ["2023-01-01", "2023-01-02"]
    assert identify_most_common_delimiter(ts) == "-"


def test_infer_datetime_format_from_samples():
    samples = ["2023-01-01T12:00:00Z", "2023-01-02T13:00:00Z"]
    result = infer_datetime_format_from_samples(samples)
    assert result["accuracy"] == 1.0


def test_group_timestamps_by_component_count():
    groups = group_timestamps_by_component_count(["2023-01-01", "2023-01-01 12:00"])
    assert len(groups) == 2


def test_identify_format_groups():
    ts = ["2023-01-01T12:00:00Z", "01-Jan-2023"]
    groups = identify_format_groups(ts)
    assert len(groups) >= 1


def test_analyze_heterogeneous_timestamp_formats():
    ts = ["2023-01-01T12:00:00Z", "01-Jan-2023"]
    result = analyze_heterogeneous_timestamp_formats(ts)
    assert isinstance(result, dict)
