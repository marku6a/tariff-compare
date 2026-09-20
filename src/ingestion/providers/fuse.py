import csv
from pathlib import Path

from ingestion.models import RawBatch

def read(source: Path) -> RawBatch:
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = tuple(reader.fieldnames or ())
        rows = tuple(dict(row) for row in reader)
    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=source,
        headers=headers,
        rows=rows
    )