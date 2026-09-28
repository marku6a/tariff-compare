from pathlib import Path

import pytest

from ingestion.models import RawBatch, RawValue
from ingestion.validation import validate_batch
from ingestion.raw_schema import RAW_SCHEMA_HEADERS


def test_rejects_batch_without_rows():
    batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("header_only.csv"),
        timestamp_boundary="end",
        timestamp_timezone="Europe/London",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=RAW_SCHEMA_HEADERS,
        rows=(),
    )

    with pytest.raises(ValueError, match="Batch must contain at least one row"):
        validate_batch(batch)


@pytest.mark.parametrize(
    ("bad_row_index", "bad_header"), [(0, "meter_id"), (1, "energy_value")]
)
def test_rejects_row_with_structurally_missing_value(
    bad_row_index: int, bad_header: str
):
    rows: list[dict[str, RawValue]] = [
        {
            "meter_id": "meter-123",
            "interval_timestamp": "September 12, 2026, 20:00",
            "energy_value": "100",
            "source_fields": "{}",
        },
        {
            "meter_id": "meter-456",
            "interval_timestamp": "September 12, 2026, 21:00",
            "energy_value": "200",
            "source_fields": "{}",
        },
    ]

    rows[bad_row_index][bad_header] = None

    batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("short_row.csv"),
        timestamp_boundary="end",
        timestamp_timezone="Europe/London",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=RAW_SCHEMA_HEADERS,
        rows=tuple(rows),
    )

    expected_row_number = bad_row_index + 1

    with pytest.raises(ValueError, match=rf"Row {expected_row_number}.*{bad_header}"):
        validate_batch(batch)


def test_accepts_empty_strings():
    rows = (
        {
            "meter_id": "meter-123",
            "interval_timestamp": "September 12, 2026, 20:00",
            "energy_value": "",
            "source_fields": "{}",
        },
    )

    batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("header_only.csv"),
        timestamp_boundary="end",
        timestamp_timezone="Europe/London",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=RAW_SCHEMA_HEADERS,
        rows=rows,
    )
    validate_batch(batch)
