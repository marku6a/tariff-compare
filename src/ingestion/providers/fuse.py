import csv
from pathlib import Path

from ingestion.models import RawBatch

REQUIRED_HEADERS = frozenset(
    {
        "supply_fid",
        "ts_utc",
        "value_Wh",
    }
)

def read(source: Path) -> RawBatch:
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = tuple(reader.fieldnames or ())

        missing_headers = REQUIRED_HEADERS - set(headers)
        
        if missing_headers:
            raise ValueError(
                "Missing required Fuse headers: "
                f"{', '.join(sorted(missing_headers))}"
            )
        
        rows = tuple(dict(row) for row in reader)

    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=source,
        headers=headers,
        rows=rows
    )