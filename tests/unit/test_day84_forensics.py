import pandas as pd
import pytest

from scripts.analysis.day84_forensics import _segment_bounds, validate_prediction_frame


def _frame(day=84):
    return pd.DataFrame(
        {
            "day": [day, day],
            "timestamp": ["00:00:00", "00:00:01"],
            "timestamp_seconds": [0, 1],
            "target": [0.1, -0.2],
            "prediction": [0.2, -0.1],
            "residual": [0.1, 0.1],
        }
    )


def test_day84_prediction_schema_and_residual_alignment_are_validated():
    validate_prediction_frame(_frame(), 84)
    with pytest.raises(ValueError, match="residual"):
        validate_prediction_frame(_frame().assign(residual=[0.0, 0.0]), 84)


def test_holdout_prediction_partition_is_rejected():
    with pytest.raises(ValueError, match="holdout"):
        validate_prediction_frame(_frame(day=86), 86)


def test_intraday_segment_boundaries_preserve_remainder_in_final_segment():
    assert _segment_bounds(12242) == [0, 2448, 4896, 7344, 9792, 12242]
