import pytest
import csv
import json
from pathlib import Path
from ingestion.providers import fuse
from ingestion.raw_schema import RAW_SCHEMA_HEADERS

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fuse" / "valid.csv"

FUSE_HEADERS = (
    "supply_fid",
    "ts_utc",
    "sequence_num",
    "value_Wh",
    "ts_tma_knew_utc",
    "is_latest",
    "created_at_utc",
    "_peerdb_synced_at",
    "_peerdb_is_deleted",
    "_peerdb_version",
    "interval_status",
    "version",
)

REQUIRED_FUSE_HEADERS = (
    "supply_fid",
    "ts_utc",
    "value_Wh",
)


def test_reads_fuse_fixture():
    batch = fuse.read(FIXTURE)

    assert batch.provider == "fuse"
    assert batch.source_kind == "meter_readings"

    assert batch.headers == RAW_SCHEMA_HEADERS

    assert len(batch.rows) == 3

    assert batch.rows[0]["meter_id"] == "9672a909-fe74-49ae-bf00-84c82b4edd47"
    assert batch.rows[0]["interval_timestamp"] == "September 14, 2026, 21:00"
    assert batch.rows[0]["energy_value"] == "140"
    assert json.loads(str(batch.rows[0]["source_fields"])) == {
        "sequence_num": "0",
        "ts_tma_knew_utc": "January 1, 1970, 00:00",
        "is_latest": "true",
        "created_at_utc": "September 14, 2026, 21:21",
        "_peerdb_synced_at": "September 14, 2026, 21:21",
        "_peerdb_is_deleted": "0",
        "_peerdb_version": "1,789,420,881,910,711,492",
        "interval_status": "NOT_APPLICABLE",
        "version": "0",
    }

    assert batch.timestamp_boundary == "end"
    assert batch.timestamp_timezone == "UTC"
    assert batch.energy_unit == "wh"
    assert batch.interval_duration_minutes == 30


@pytest.mark.parametrize("missing_header", REQUIRED_FUSE_HEADERS)
def test_rejects_missing_required_header(
    tmp_path: Path,
    missing_header: str,
):
    headers = [header for header in REQUIRED_FUSE_HEADERS if header != missing_header]

    source = tmp_path / "missing_header.csv"

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: "example" for header in headers})

    with pytest.raises(
        ValueError,
        match=rf"{missing_header}",
    ):
        fuse.read(source)


def test_accepts_missing_optional_headers(
    tmp_path: Path,
):
    headers = REQUIRED_FUSE_HEADERS

    source = tmp_path / "missing_optional_headers.csv"

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: "example" for header in headers})

    batch = fuse.read(source)

    assert batch.headers == RAW_SCHEMA_HEADERS
    assert batch.rows[0]["meter_id"] == "example"
    assert batch.rows[0]["interval_timestamp"] == "example"
    assert batch.rows[0]["energy_value"] == "example"
    assert json.loads(str(batch.rows[0]["source_fields"])) == {}


def test_accepts_unexpected_fuse_header(tmp_path: Path):
    source = tmp_path / "unexpected_header.csv"
    headers = (*REQUIRED_FUSE_HEADERS, "extra_column")

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: header for header in headers})

    batch = fuse.read(source)

    assert batch.headers == RAW_SCHEMA_HEADERS
    assert batch.rows[0]["meter_id"] == "supply_fid"
    assert batch.rows[0]["interval_timestamp"] == "ts_utc"
    assert batch.rows[0]["energy_value"] == "value_Wh"
    assert json.loads(str(batch.rows[0]["source_fields"])) == {
        header: header for header in headers if header not in REQUIRED_FUSE_HEADERS
    }


def test_accepts_reordered_fuse_headers(tmp_path: Path):
    source = tmp_path / "reordered_headers.csv"
    headers = tuple(reversed(FUSE_HEADERS))

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: header for header in headers})

    batch = fuse.read(source)

    assert batch.headers == RAW_SCHEMA_HEADERS
    assert batch.rows[0]["meter_id"] == "supply_fid"
    assert batch.rows[0]["interval_timestamp"] == "ts_utc"
    assert batch.rows[0]["energy_value"] == "value_Wh"
    assert json.loads(str(batch.rows[0]["source_fields"])) == {
        header: header for header in FUSE_HEADERS if header not in REQUIRED_FUSE_HEADERS
    }


def test_rejects_structurally_short_provider_only_field(tmp_path: Path):
    source = tmp_path / "short_row.csv"

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(FUSE_HEADERS)
        writer.writerow(["example"] * (len(FUSE_HEADERS) - 1))

    missing_header = FUSE_HEADERS[-1]
    assert missing_header not in REQUIRED_FUSE_HEADERS
    with pytest.raises(ValueError, match=missing_header):
        fuse.read(source)
