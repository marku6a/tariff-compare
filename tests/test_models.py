from dataclasses import replace
from pathlib import Path

import pytest

from ingestion.models import RawBatch


@pytest.fixture
def meter_batch() -> RawBatch:
    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("readings.csv"),
        timestamp_boundary="end",
        timestamp_timezone="Europe/London",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=("supply_fid", "ts_utc", "value_Wh"),
        rows=(),
    )


@pytest.fixture
def tariff_batch(meter_batch: RawBatch) -> RawBatch:
    return replace(
        meter_batch,
        source_kind="tariff",
        timestamp_boundary=None,
        timestamp_timezone=None,
        energy_unit=None,
        interval_duration_minutes=None,
    )


def test_accepts_meter_reading_metadata(meter_batch: RawBatch):
    assert meter_batch.timestamp_boundary == "end"
    assert meter_batch.timestamp_timezone == "Europe/London"
    assert meter_batch.energy_unit == "wh"
    assert meter_batch.interval_duration_minutes == 30

    other_provider = replace(
        meter_batch,
        timestamp_boundary="start",
        timestamp_timezone="UTC",
        energy_unit="kwh",
        interval_duration_minutes=60,
    )
    assert other_provider.timestamp_boundary == "start"
    assert other_provider.energy_unit == "kwh"


def test_accepts_tariff_without_interval_metadata(tariff_batch: RawBatch):
    assert tariff_batch.timestamp_boundary is None
    assert tariff_batch.timestamp_timezone is None
    assert tariff_batch.energy_unit is None
    assert tariff_batch.interval_duration_minutes is None


def test_rejects_invalid_source_kind(meter_batch: RawBatch):
    with pytest.raises(ValueError, match="Invalid source kind"):
        replace(meter_batch, source_kind="other")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("timestamp_boundary", None, "Invalid timestamp boundary"),
        ("timestamp_boundary", "middle", "Invalid timestamp boundary"),
        ("energy_unit", None, "Invalid energy unit"),
        ("energy_unit", "mwh", "Invalid energy unit"),
        ("timestamp_timezone", None, "nonblank timezone"),
        ("timestamp_timezone", "", "nonblank timezone"),
        ("timestamp_timezone", "  ", "nonblank timezone"),
        ("interval_duration_minutes", None, "positive interval duration"),
        ("interval_duration_minutes", 0, "positive interval duration"),
        ("interval_duration_minutes", -30, "positive interval duration"),
        ("interval_duration_minutes", 30.5, "positive interval duration"),
        ("interval_duration_minutes", True, "positive interval duration"),
    ],
)
def test_rejects_invalid_meter_metadata(
    meter_batch: RawBatch, field: str, value: object, message: str
):
    with pytest.raises(ValueError, match=message):
        replace(meter_batch, **{field: value})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("timestamp_boundary", "end", "Tariff should not have timestamp boundary"),
        ("timestamp_timezone", "UTC", "Tariff should not have timezone"),
        ("energy_unit", "wh", "Tariff should not have energy unit"),
        ("interval_duration_minutes", 30, "Tariff should not have interval duration"),
    ],
)
def test_rejects_interval_metadata_for_tariff(
    tariff_batch: RawBatch, field: str, value: object, message: str
):
    with pytest.raises(ValueError, match=message):
        replace(tariff_batch, **{field: value})


@pytest.mark.parametrize("bad_row_index", [0, 1])
def test_rejects_row_with_unexpected_key(meter_batch: RawBatch, bad_row_index: int):
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
        replace(meter_batch, source_path=Path("surplus_value.csv"), rows=tuple(rows))


@pytest.mark.parametrize(
    ("bad_row_index", "missing_header"), [(0, "supply_fid"), (1, "value_Wh")]
)
def test_rejects_row_with_missing_key(
    meter_batch: RawBatch, bad_row_index: int, missing_header: str
):
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
        replace(meter_batch, source_path=Path("missing_key.csv"), rows=tuple(rows))


def test_rejects_duplicate_headers(meter_batch: RawBatch):
    with pytest.raises(ValueError, match="Headers must be unique"):
        replace(
            meter_batch,
            source_path=Path("duplicate_headers.csv"),
            headers=("supply_fid", "value_Wh", "value_Wh"),
        )
