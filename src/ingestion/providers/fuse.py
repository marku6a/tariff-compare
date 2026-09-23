import csv
from pathlib import Path

from ingestion.models import RawBatch

EXPECTED_HEADERS = frozenset(
    {
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
    }
)


def read(source: Path) -> RawBatch:
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = tuple(reader.fieldnames or ())

        actual_headers = set(headers)
        missing_headers = EXPECTED_HEADERS - actual_headers
        unexpected_headers = actual_headers - EXPECTED_HEADERS

        if missing_headers or unexpected_headers:
            raise ValueError(
                "Fuse headers do not match the supported export. "
                f"Missing: {sorted(missing_headers)}. "
                f"Unexpected: {sorted(unexpected_headers)}."
            )

        rows = tuple(dict(row) for row in reader)

    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=source,
        headers=headers,
        rows=rows,
    )
