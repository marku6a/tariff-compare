from pathlib import Path

import pytest

from ingestion.models import RawBatch


@pytest.mark.parametrize("bad_row_index", [0, 1])
def test_rejects_row_with_unexpected_key(bad_row_index: int):
    rows = [
        {
            "supply_fid": "meter-123",
            "ts_utc": "September 12, 2026, 20:00",
            "value_Wh": "100",
        },
        {
            "supply_fid": "meter-456",
            "ts_utc": "September 12, 2026, 21:00",
            "value_Wh": "200",
        },
    ]

    rows[bad_row_index]["extra_column"] = "unexpected"

    bad_row_number = bad_row_index + 1

    with pytest.raises(
        ValueError,
        match=rf"Row {bad_row_number}.*Unexpected: \['extra_column'\]",
    ):
        RawBatch(
            provider="fuse",
            source_kind="meter_readings",
            source_path=Path("surplus_value.csv"),
            headers=("supply_fid", "ts_utc", "value_Wh"),
            rows=tuple(rows),
        )


@pytest.mark.parametrize(
    ("bad_row_index", "missing_header"), [(0, "supply_fid"), (1, "value_Wh")]
)
def test_rejects_row_with_missing_key(bad_row_index: int, missing_header: str):
    rows = [
        {
            "supply_fid": "meter-123",
            "ts_utc": "September 12, 2026, 20:00",
            "value_Wh": "100",
        },
        {
            "supply_fid": "meter-456",
            "ts_utc": "September 12, 2026, 21:00",
            "value_Wh": "200",
        },
    ]

    del rows[bad_row_index][missing_header]

    bad_row_number = bad_row_index + 1
    with pytest.raises(
        ValueError,
        match=rf"Row {bad_row_number}.*Missing: \['{missing_header}'\]",
    ):
        RawBatch(
            provider="fuse",
            source_kind="meter_readings",
            source_path=Path("missing_key.csv"),
            headers=("supply_fid", "ts_utc", "value_Wh"),
            rows=tuple(rows),
        )


def test_rejects_duplicate_headers():
    with pytest.raises(ValueError, match="Headers must be unique"):
        RawBatch(
            provider="fuse",
            source_kind="meter_readings",
            source_path=Path("duplicate_headers.csv"),
            headers=("supply_fid", "value_Wh", "value_Wh"),
            rows=(),
        )
