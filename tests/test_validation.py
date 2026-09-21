from pathlib import Path

import pytest

from ingestion.models import RawBatch, RawValue
from ingestion.validation import validate_batch


def test_rejects_batch_without_rows():
    batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("header_only.csv"),
        headers=(
            "supply_fid",
            "ts_utc",
            "value_Wh",
        ),
        rows=(),
    )

    with pytest.raises(ValueError, match="Batch must contain at least one row"):
        validate_batch(batch)


@pytest.mark.parametrize(
    ("bad_row_index", "bad_header"), [(0, "supply_fid"), (1, "value_Wh")]
)
def test_rejects_row_with_structurally_missing_value(
    bad_row_index: int, bad_header: str
):
    rows: list[dict[str, RawValue]] = [
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

    rows[bad_row_index][bad_header] = None

    batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("short_row.csv"),
        headers=(
            "supply_fid",
            "ts_utc",
            "value_Wh",
        ),
        rows=tuple(rows),
    )

    expected_row_number = bad_row_index + 1

    with pytest.raises(ValueError, match=rf"Row {expected_row_number}.*{bad_header}"):
        validate_batch(batch)
