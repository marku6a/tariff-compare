from pathlib import Path
from dataclasses import replace
from uuid import UUID
from datetime import UTC, datetime

import duckdb
import pytest

from ingestion.models import RawBatch
from ingestion.raw_schema import METER_READINGS_RAW_HEADERS
from ingestion.duckdb import write_batch


@pytest.fixture
def meter_batch() -> RawBatch:
    return RawBatch(
        provider="fuse",
        source_kind="meter_readings",
        source_path=Path("data/landing/meter_readings/example.csv"),
        timestamp_boundary="end",
        timestamp_timezone="UTC",
        energy_unit="wh",
        interval_duration_minutes=30,
        headers=METER_READINGS_RAW_HEADERS,
        rows=(
            {
                "meter_id": "meter123",
                "interval_timestamp": "September 12, 2026, 20:00",
                "energy_value": "100",
                "source_fields": '{"sequence_num": "0", "is_latest": "true"}',
            },
            {
                "meter_id": "meter456",
                "interval_timestamp": "banana",
                "energy_value": "200",
                "source_fields": '{"sequence_num": "1", "is_latest": "true"}',
            },
        ),
    )


def test_writes_meter_readings_and_ingestion_metadata(
    tmp_path: Path, meter_batch: RawBatch
):
    database_path = tmp_path / "raw.duckdb"
    import_id = UUID("12345678-1234-5678-1234-567812345678")
    ingested_at = datetime(2026, 9, 21, 10, 30, tzinfo=UTC)

    write_batch(
        database_path,
        meter_batch,
        import_id=import_id,
        source_sha256="abc123",
        ingested_at=ingested_at,
    )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        raw_rows = connection.execute("""
            select 
                meter_id,
                interval_timestamp,
                energy_value,
                source_fields,
                import_id,
                source_row_number
            from
                raw.meter_readings
            order by
                source_row_number
            """).fetchall()

        ingestion_file = connection.execute("""
            select
                import_id,
                provider,
                source_kind,
                source_path,
                source_sha256,
                row_count,
                ingested_at,
                timestamp_boundary,
                timestamp_timezone,
                energy_unit,
                interval_duration_minutes
            from
                raw.ingestion_files
            """).fetchall()

        source_column_types = dict(connection.execute("""
            select
                column_name, data_type
            from
                information_schema.columns
            where
                table_schema = 'raw'
                and table_name = 'meter_readings'
                and column_name in ('meter_id', 'interval_timestamp', 'energy_value', 'source_fields')
            """).fetchall())

        assert raw_rows == [
            (
                "meter123",
                "September 12, 2026, 20:00",
                "100",
                '{"sequence_num": "0", "is_latest": "true"}',
                import_id,
                1,
            ),
            (
                "meter456",
                "banana",
                "200",
                '{"sequence_num": "1", "is_latest": "true"}',
                import_id,
                2,
            ),
        ]

        assert ingestion_file == [
            (
                import_id,
                "fuse",
                "meter_readings",
                "data/landing/meter_readings/example.csv",
                "abc123",
                2,
                ingested_at,
                "end",
                "UTC",
                "wh",
                30,
            )
        ]

        assert source_column_types == {
            "meter_id": "VARCHAR",
            "interval_timestamp": "VARCHAR",
            "energy_value": "VARCHAR",
            "source_fields": "VARCHAR",
        }


@pytest.mark.parametrize(
    ("headers", "row"),
    [
        (
            ("meter_id", "interval_timestamp", "source_fields"),
            {
                "meter_id": "meter123",
                "interval_timestamp": "September 12, 2026, 20:00",
                "source_fields": "{}",
            },
        ),
        (
            (*METER_READINGS_RAW_HEADERS, "extra_column"),
            {
                "meter_id": "meter123",
                "interval_timestamp": "September 12, 2026, 20:00",
                "energy_value": "100",
                "source_fields": "{}",
                "extra_column": "unexpected",
            },
        ),
    ],
    ids=["missing-canonical-header", "extra-header"],
)
def test_rejects_noncanonical_headers(
    tmp_path: Path, meter_batch: RawBatch, headers, row
):
    database_path = tmp_path / "raw.duckdb"
    import_id = UUID("12345678-1234-5678-1234-567812345678")
    ingested_at = datetime(2026, 9, 21, 10, 30, tzinfo=UTC)

    bad_batch = replace(meter_batch, headers=headers, rows=(row,))

    with pytest.raises(ValueError, match="raw schema"):
        write_batch(
            database_path,
            bad_batch,
            import_id=import_id,
            source_sha256="abc123",
            ingested_at=ingested_at,
        )

    assert not database_path.exists()
