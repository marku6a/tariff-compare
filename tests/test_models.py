from dataclasses import replace
from pathlib import Path

import pytest

from ingestion.models import MeterReadingMetadata, RawBatch
from ingestion.raw_schema import TARIFF_RAW_HEADERS


@pytest.fixture
def meter_batch() -> RawBatch:
    return RawBatch(
        source_format="fuse_csv",
        source_kind="meter_readings",
        source_path=Path("readings.csv"),
        meter_metadata=MeterReadingMetadata(
            timestamp_boundary="end",
            timestamp_timezone="Europe/London",
            energy_unit="wh",
            interval_duration_minutes=30,
        ),
        headers=("supply_fid", "ts_utc", "value_Wh"),
        rows=(),
    )


@pytest.fixture
def tariff_batch() -> RawBatch:
    return RawBatch(
        source_format="tariff_csv",
        source_kind="tariff",
        source_path=Path("tariffs.csv"),
        headers=TARIFF_RAW_HEADERS,
        rows=(),
    )


def test_accepts_meter_reading_metadata(meter_batch: RawBatch):
    metadata = meter_batch.meter_metadata
    assert metadata is not None
    assert metadata.timestamp_boundary == "end"
    assert metadata.timestamp_timezone == "Europe/London"
    assert metadata.energy_unit == "wh"
    assert metadata.interval_duration_minutes == 30

    other_metadata = replace(
        metadata,
        timestamp_boundary="start",
        timestamp_timezone="UTC",
        energy_unit="kwh",
        interval_duration_minutes=60,
    )
    other_batch = replace(meter_batch, meter_metadata=other_metadata)
    assert other_batch.meter_metadata == other_metadata
    assert other_metadata.timestamp_boundary == "start"
    assert other_metadata.energy_unit == "kwh"


def test_accepts_tariff_without_interval_metadata(tariff_batch: RawBatch):
    assert tariff_batch.meter_metadata is None


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
    assert meter_batch.meter_metadata is not None
    with pytest.raises(ValueError, match=message):
        replace(meter_batch.meter_metadata, **{field: value})


@pytest.mark.parametrize("metadata", [None, {}], ids=["missing", "wrong-type"])
def test_rejects_meter_batch_without_valid_metadata(meter_batch: RawBatch, metadata):
    with pytest.raises(ValueError, match="Meter readings require MeterReadingMetadata"):
        replace(meter_batch, meter_metadata=metadata)


def test_rejects_interval_metadata_for_tariff(
    tariff_batch: RawBatch, meter_batch: RawBatch
):
    with pytest.raises(ValueError, match="Tariff should not have meter metadata"):
        replace(tariff_batch, meter_metadata=meter_batch.meter_metadata)


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
