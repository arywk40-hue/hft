#!/usr/bin/env python3
"""Run PHASE 1 dataset reconnaissance on sampled development days.

The implementation uses only Python's standard library. It streams each CSV
one row at a time, never concatenates days, and rejects holdout day IDs in the
sample set. Raw CSV files are opened read-only and are never rewritten.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev


PB_LADDER = (15, 30, 90, 180, 270, 360, 900, 1800, 2700, 4500, 5400, 10800)
OTHER_LADDER = (5, 10, 30, 60, 90, 120, 300, 600, 900, 1500, 1800, 3600)
FEATURE_RE = re.compile(
    r"^(?P<family>PB|VB|PV|BB|V)(?P<body>.*?)(?:_T(?P<suffix>\d+))?$"
)
TIME_RE = re.compile(r"^(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})$")
NAN_TOKENS = {"", "nan", "na", "null", "none"}
INF_TOKENS = {"inf", "+inf", "infinity", "+infinity", "-inf", "-infinity"}


@dataclass(frozen=True)
class FeatureMeta:
    feature: str
    family: str
    subfamily: str
    suffix: str
    nominal_window_seconds: int | None


def parse_feature(
    name: str,
    pb_ladder: tuple[int, ...] = PB_LADDER,
    other_ladder: tuple[int, ...] = OTHER_LADDER,
) -> FeatureMeta:
    match = FEATURE_RE.fullmatch(name)
    if match is None:
        return FeatureMeta(name, "unknown", "", "", None)
    family = match.group("family")
    body = match.group("body")
    suffix = match.group("suffix") or ""
    subfamily = f"{family}{body}" if body else family
    nominal = None
    if suffix:
        suffix_index = int(suffix)
        ladder = pb_ladder if family == "PB" else other_ladder
        if 1 <= suffix_index <= len(ladder):
            nominal = ladder[suffix_index - 1]
    return FeatureMeta(name, family, subfamily, suffix, nominal)


def parse_time_seconds(value: str) -> int | None:
    match = TIME_RE.fullmatch(value.strip())
    if not match:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second"))
    if minute >= 60 or second >= 60:
        return None
    return hour * 3600 + minute * 60 + second


def header_hash(header: list[str]) -> str:
    return hashlib.sha256("\x1f".join(header).encode("utf-8")).hexdigest()


def numeric_value(cell: str) -> tuple[str, float | None]:
    """Classify a CSV cell without coercing missing values to zero."""

    token = cell.strip().lower()
    if token in NAN_TOKENS:
        return "nan", None
    if token in INF_TOKENS:
        return "inf", None
    try:
        value = float(cell)
    except ValueError:
        return "non_numeric", None
    if math.isnan(value):
        return "nan", None
    if math.isinf(value):
        return "inf", None
    return "valid", value


def safe_std(sum_value: float, sum_sq: float, count: int) -> float:
    if count < 2:
        return float("nan")
    variance = (sum_sq - (sum_value * sum_value) / count) / (count - 1)
    return math.sqrt(max(variance, 0.0))


def inspect_day(
    path: Path,
    day: int,
    reference_header: list[str] | None = None,
    pb_ladder: tuple[int, ...] = PB_LADDER,
    other_ladder: tuple[int, ...] = OTHER_LADDER,
) -> tuple[dict, list[dict], list[str], list[FeatureMeta]]:
    warmup: list[dict] = []
    with path.open("r", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {path}") from exc
        if len(header) < 2 or header[:2] != ["Time", "Price"]:
            raise ValueError(f"unexpected first columns in {path}: {header[:2]}")
        features = [parse_feature(name, pb_ladder, other_ladder) for name in header[2:]]
        first_valid = [None] * len(features)
        first_valid_seconds = [None] * len(features)
        total_nan = [0] * len(features)
        total_inf = [0] * len(features)
        non_numeric = [0] * len(features)
        seen_valid = [0] * len(features)
        candidate_numeric = [True] * len(header[1:])
        timestamps_seen: set[int] = set()
        interval_counts: Counter[int] = Counter()
        row_count = 0
        duplicate_timestamps = 0
        out_of_order = 0
        malformed_time_rows = 0
        previous_seconds: int | None = None
        start_seconds: int | None = None
        end_seconds: int | None = None
        price_count = 0
        price_nan = 0
        price_inf = 0
        price_zero = 0
        price_negative = 0
        price_sum = 0.0
        price_sum_sq = 0.0
        price_min = float("inf")
        price_max = float("-inf")
        zero_price_changes = 0
        previous_price: float | None = None
        short_rows = 0
        long_rows = 0
        numeric_nan_total = 0
        numeric_inf_total = 0

        for row_index, row in enumerate(reader, start=1):
            row_count += 1
            if len(row) < len(header):
                short_rows += 1
                row = row + [""] * (len(header) - len(row))
            elif len(row) > len(header):
                long_rows += 1
                candidate_numeric = [False] * len(header[1:])
                row = row[: len(header)]

            time_value = parse_time_seconds(row[0])
            if time_value is None:
                malformed_time_rows += 1
            else:
                if start_seconds is None:
                    start_seconds = time_value
                end_seconds = time_value
                if time_value in timestamps_seen:
                    duplicate_timestamps += 1
                timestamps_seen.add(time_value)
                if previous_seconds is not None:
                    delta = time_value - previous_seconds
                    interval_counts[delta] += 1
                    if delta <= 0:
                        out_of_order += 1
                previous_seconds = time_value

            price_kind, price = numeric_value(row[1])
            if price_kind == "valid":
                assert price is not None
                price_count += 1
                price_sum += price
                price_sum_sq += price * price
                price_min = min(price_min, price)
                price_max = max(price_max, price)
                if price == 0:
                    price_zero += 1
                if price < 0:
                    price_negative += 1
                if previous_price == price:
                    zero_price_changes += 1
                previous_price = price
            elif price_kind == "nan":
                price_nan += 1
                previous_price = None
            elif price_kind == "inf":
                price_inf += 1
                previous_price = None
            else:
                candidate_numeric[0] = False
                previous_price = None

            for feature_index, cell in enumerate(row[2:]):
                kind, value = numeric_value(cell)
                if kind == "valid":
                    seen_valid[feature_index] += 1
                    if first_valid[feature_index] is None:
                        first_valid[feature_index] = row_index
                        first_valid_seconds[feature_index] = time_value
                elif kind == "nan":
                    total_nan[feature_index] += 1
                    numeric_nan_total += 1
                elif kind == "inf":
                    total_inf[feature_index] += 1
                    numeric_inf_total += 1
                else:
                    non_numeric[feature_index] += 1
                    candidate_numeric[feature_index + 1] = False

        if reference_header is None:
            reference_header = header
        missing_columns = sorted(set(reference_header) - set(header))
        unexpected_columns = sorted(set(header) - set(reference_header))
        duplicate_columns = len(header) - len(set(header))
        mode_interval, mode_count = (interval_counts.most_common(1) or [(None, 0)])[0]
        one_second_intervals = interval_counts.get(1, 0)
        non_one_second_intervals = sum(count for delta, count in interval_counts.items() if delta != 1)
        missing_seconds = sum(max(delta - 1, 0) * count for delta, count in interval_counts.items() if delta > 1)
        profile = {
            "day": day,
            "source_path": str(path),
            "row_count": row_count,
            "column_count": len(header),
            "numeric_column_count": sum(candidate_numeric),
            "header_sha256": header_hash(header),
            "start_time": f"{start_seconds // 3600:02d}:{(start_seconds % 3600) // 60:02d}:{start_seconds % 60:02d}" if start_seconds is not None else "",
            "end_time": f"{end_seconds // 3600:02d}:{(end_seconds % 3600) // 60:02d}:{end_seconds % 60:02d}" if end_seconds is not None else "",
            "distinct_timestamps": len(timestamps_seen),
            "duplicate_timestamps": duplicate_timestamps,
            "out_of_order": out_of_order,
            "frequency_mode_seconds": mode_interval if mode_interval is not None else "",
            "frequency_mode_count": mode_count,
            "one_second_intervals": one_second_intervals,
            "non_one_second_intervals": non_one_second_intervals,
            "missing_seconds": missing_seconds,
            "malformed_time_rows": malformed_time_rows,
            "price_min": price_min if price_count else "",
            "price_max": price_max if price_count else "",
            "price_mean": price_sum / price_count if price_count else "",
            "price_std": safe_std(price_sum, price_sum_sq, price_count) if price_count else "",
            "price_valid_count": price_count,
            "price_nan_count": price_nan,
            "price_inf_count": price_inf,
            "price_zero_count": price_zero,
            "price_negative_count": price_negative,
            "zero_price_change_count": zero_price_changes,
            "numeric_nan_count": numeric_nan_total,
            "numeric_inf_count": numeric_inf_total,
            "short_rows": short_rows,
            "long_rows": long_rows,
            "schema_missing_columns": "|".join(missing_columns),
            "schema_unexpected_columns": "|".join(unexpected_columns),
            "duplicate_column_count": duplicate_columns,
        }
        for index, meta in enumerate(features):
            first_position = first_valid[index]
            first_seconds = first_valid_seconds[index]
            warmup.append(
                {
                    "day": day,
                    "feature": meta.feature,
                    "family": meta.family,
                    "subfamily": meta.subfamily,
                    "suffix": meta.suffix,
                    "nominal_window_seconds": meta.nominal_window_seconds if meta.nominal_window_seconds is not None else "",
                    "first_valid_position": first_position if first_position is not None else "",
                    "first_valid_timestamp": (
                        f"{first_seconds // 3600:02d}:{(first_seconds % 3600) // 60:02d}:{first_seconds % 60:02d}"
                        if first_seconds is not None
                        else ""
                    ),
                    "actual_warmup_seconds": (first_seconds - start_seconds) if first_seconds is not None and start_seconds is not None else "",
                    "leading_nan_count": (first_position - 1) if first_position is not None else row_count,
                    "total_nan_count": total_nan[index],
                    "total_inf_count": total_inf[index],
                    "valid_count": seen_valid[index],
                    "non_numeric_count": non_numeric[index],
                }
            )
        return profile, warmup, header, features


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(
    repo_root: Path,
    sample_days: list[int],
    pb_ladder: tuple[int, ...] = PB_LADDER,
    other_ladder: tuple[int, ...] = OTHER_LADDER,
) -> None:
    if any(day < 1 or day > 85 for day in sample_days):
        raise ValueError("PHASE 1 sample days must be within development Days 1-85")
    if len(set(sample_days)) != len(sample_days):
        raise ValueError("duplicate sample day IDs")
    data_dir = repo_root / "data"
    profiles: list[dict] = []
    warmups: list[dict] = []
    reference_header: list[str] | None = None
    reference_features: list[FeatureMeta] | None = None
    headers_by_day: dict[int, list[str]] = {}
    for day in sample_days:
        path = data_dir / f"day{day}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"required sampled development day is missing: {path}")
        profile, day_warmup, header, features = inspect_day(
            path, day, reference_header, pb_ladder, other_ladder
        )
        if reference_header is None:
            reference_header = header
            reference_features = features
        profiles.append(profile)
        warmups.extend(day_warmup)
        headers_by_day[day] = header

    assert reference_header is not None
    assert reference_features is not None
    reference_set = set(reference_header)
    schema_rows = []
    for profile in profiles:
        day = profile["day"]
        header = headers_by_day[day]
        schema_rows.append(
            {
                "day": day,
                "column_count": len(header),
                "reference_column_count": len(reference_header),
                "header_sha256": header_hash(header),
                "reference_header_sha256": header_hash(reference_header),
                "same_order": header == reference_header,
                "same_set": set(header) == reference_set,
                "missing_columns": profile["schema_missing_columns"],
                "unexpected_columns": profile["schema_unexpected_columns"],
                "duplicate_column_count": profile["duplicate_column_count"],
            }
        )

    inventory_rows = []
    for meta in reference_features:
        day_presence = [meta.feature in headers_by_day[day] for day in sample_days]
        inventory_rows.append(
            {
                "feature": meta.feature,
                "family": meta.family,
                "subfamily": meta.subfamily,
                "suffix": meta.suffix,
                "nominal_window_seconds": meta.nominal_window_seconds if meta.nominal_window_seconds is not None else "",
                "sample_days_present": sum(day_presence),
                "sample_days_total": len(sample_days),
            }
        )

    ladder_rows = []
    by_feature: dict[str, list[dict]] = {}
    for row in warmups:
        by_feature.setdefault(row["feature"], []).append(row)
    for meta in reference_features:
        rows = by_feature[meta.feature]
        observed = [row["actual_warmup_seconds"] for row in rows if row["actual_warmup_seconds"] != ""]
        nominal = meta.nominal_window_seconds
        deltas = [value - nominal for value in observed] if nominal is not None else []
        ladder_rows.append(
            {
                "feature": meta.feature,
                "family": meta.family,
                "subfamily": meta.subfamily,
                "suffix": meta.suffix,
                "nominal_window_seconds": nominal if nominal is not None else "",
                "sample_days_with_valid_value": len(observed),
                "observed_warmup_min_seconds": min(observed) if observed else "",
                "observed_warmup_median_seconds": median(observed) if observed else "",
                "observed_warmup_mean_seconds": mean(observed) if observed else "",
                "observed_warmup_max_seconds": max(observed) if observed else "",
                "delta_from_nominal_min_seconds": min(deltas) if deltas else "",
                "delta_from_nominal_median_seconds": median(deltas) if deltas else "",
                "delta_from_nominal_max_seconds": max(deltas) if deltas else "",
                "exact_nominal_matches": sum(delta == 0 for delta in deltas) if deltas else "",
                "note": "nominal window is a hypothesis; actual warm-up is reported, not forced",
            }
        )

    output_dir = repo_root / "results" / "phase1"
    write_csv(output_dir / "schema_profile.csv", schema_rows, list(schema_rows[0]))
    write_csv(output_dir / "feature_inventory.csv", inventory_rows, list(inventory_rows[0]))
    write_csv(output_dir / "sample_day_profile.csv", profiles, list(profiles[0]))
    write_csv(output_dir / "warmup_profile.csv", warmups, list(warmups[0]))
    write_csv(output_dir / "ladder_reconnaissance.csv", ladder_rows, list(ladder_rows[0]))

    (output_dir / "README.txt").write_text(
        "PHASE 1 reconnaissance notes\n"
        f"sample_days={','.join(map(str, sample_days))}\n"
        "scope=development days only (1-85); Days 86-108 were not opened\n"
        "missing_development_days=65-79 (recorded in PHASE 0; not silently dropped)\n"
        "method=streaming CSV read; raw files were not modified\n"
        "nominal_ladders=PB:15,30,90,180,270,360,900,1800,2700,4500,5400,10800; "
        "BB/PV/V/VB:5,10,30,60,90,120,300,600,900,1500,1800,3600\n"
        "interpretation=window values remain hypotheses until validated across all available development days\n"
    )


def load_config_lists(config_path: Path) -> dict[str, list[int]]:
    """Read the integer-list settings used by this phase's simple YAML file."""

    settings: dict[str, list[int]] = {}
    if not config_path.is_file():
        return settings
    for raw_line in config_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = (part.strip() for part in line.split(":", 1))
        if not (raw_value.startswith("[") and raw_value.endswith("]")):
            continue
        value = ast.literal_eval(raw_value)
        if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
            raise ValueError(f"expected an integer list for {key} in {config_path}")
        settings[key] = value
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--sample-days",
        type=int,
        nargs="+",
        default=None,
    )
    parser.add_argument("--pb-ladder", type=int, nargs="+", default=None)
    parser.add_argument("--other-ladder", type=int, nargs="+", default=None)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    settings = load_config_lists(args.config or repo_root / "config" / "config.yaml")
    sample_days = args.sample_days or settings.get("phase1_sample_days", [1, 2, 21, 40, 60, 64, 81, 85])
    pb_ladder = tuple(args.pb_ladder or settings.get("pb_nominal_windows_seconds", list(PB_LADDER)))
    other_ladder = tuple(args.other_ladder or settings.get("other_nominal_windows_seconds", list(OTHER_LADDER)))
    run(repo_root, sample_days, pb_ladder, other_ladder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
