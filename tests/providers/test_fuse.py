import pytest
import csv
from pathlib import Path
from ingestion.providers import fuse

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fuse" / "valid.csv"

def test_reads_fuse_fixture():
    batch = fuse.read(FIXTURE)

    assert batch.provider == "fuse"
    assert batch.source_kind == "meter_readings"

    assert batch.headers == (
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

    assert len(batch.rows) == 3

    assert batch.rows[0] == {
        "supply_fid": "9672a909-fe74-49ae-bf00-84c82b4edd47",
        "ts_utc": "September 14, 2026, 21:00",
        "sequence_num": "0",
        "value_Wh": "140",
        "ts_tma_knew_utc": "January 1, 1970, 00:00",
        "is_latest": "true",
        "created_at_utc": "September 14, 2026, 21:21",
        "_peerdb_synced_at": "September 14, 2026, 21:21",
        "_peerdb_is_deleted": "0",
        "_peerdb_version": "1,789,420,881,910,711,492",
        "interval_status": "NOT_APPLICABLE",
        "version": "0",
    }

REQUIRED_FUSE_HEADERS = (
    "supply_fid",
    "ts_utc",
    "value_Wh",
)


@pytest.mark.parametrize("missing_header", REQUIRED_FUSE_HEADERS)
def test_rejects_missing_required_fuse_header(
    tmp_path: Path,
    missing_header: str,
):
    headers = [
        header
        for header in REQUIRED_FUSE_HEADERS
        if header != missing_header
    ]

    source = tmp_path / "missing_header.csv"

    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({header: "example" for header in headers})

    with pytest.raises(
        ValueError,
        match=rf"Missing required Fuse headers:.*{missing_header}",
    ):
        fuse.read(source)
