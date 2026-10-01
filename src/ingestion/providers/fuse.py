import csv
import json
from pathlib import Path

from ingestion.models import RawBatch
from ingestion.raw_schema import RAW_SCHEMA_HEADERS
from ingestion.validation import validate_batch

FUSE_TO_RAW_HEADERS = {
    "supply_fid": "meter_id",
    "ts_utc": "interval_timestamp",
    "value_Wh": "energy_value",
}

REQUIRED_FUSE_HEADERS = frozenset(FUSE_TO_RAW_HEADERS)


def read(source: Path) -> RawBatch:
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = tuple(reader.fieldnames or ())

        actual_headers = set(headers)
        missing_required_headers = REQUIRED_FUSE_HEADERS - actual_headers

        if missing_required_headers:
            raise ValueError(
                f"Missing required Fuse headers: {sorted(missing_required_headers)}."
            )

        rows = tuple(dict(row) for row in reader)

    source_batch = RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=source,
        timestamp_boundary="end",
        timestamp_timezone="UTC",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=headers,
        rows=rows,
    )
    # Check the original fields before packing provider-only values into JSON.
    validate_batch(source_batch)

    source_only_headers = tuple(
        header for header in headers if header not in REQUIRED_FUSE_HEADERS
    )
    raw_rows = tuple(
        {
            **{
                raw_header: row[source_header]
                for source_header, raw_header in FUSE_TO_RAW_HEADERS.items()
            },
            "source_fields": json.dumps(
                {header: row[header] for header in source_only_headers},
                ensure_ascii=False,
            ),
        }
        for row in rows
    )

    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=source,
        timestamp_boundary="end",
        timestamp_timezone="UTC",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=RAW_SCHEMA_HEADERS,
        rows=raw_rows,
    )
