from pathlib import Path
from dataclasses import replace
from uuid import UUID
from datetime import UTC, datetime

import duckdb
import pytest

from ingestion.models import MeterReadingMetadata, RawBatch
from ingestion.raw_schema import METER_READINGS_RAW_HEADERS, TARIFF_RAW_HEADERS
from ingestion.duckdb import write_batch


@pytest.fixture
def meter_batch() -> RawBatch:
    return RawBatch(
        source_format="fuse_csv",
        source_kind="meter_readings",
        source_path=Path("data/landing/meter_readings/example.csv"),
        meter_metadata=MeterReadingMetadata(
            timestamp_boundary="end",
            timestamp_timezone="UTC",
            energy_unit="wh",
            interval_duration_minutes=30,
        ),
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


@pytest.fixture
def tariff_batch() -> RawBatch:
    return RawBatch(
        source_format="tariff_csv",
        source_kind="tariff",
        source_path=Path("data/landing/tariffs/tariffs_example.csv"),
        headers=TARIFF_RAW_HEADERS,
        rows=(
            {
                "tariff_id": "flat_example",
                "tariff_name": "Flat Example",
                "supplier": "Example Energy",
                "fix_length_months": "12",
                "exit_fee_pounds": "0",
                "standing_charge_pence_per_day": "55.12",
                "day_type": "ALL",
                "start_time_local": "00:00",
                "end_time_local": "24:00",
                "unit_rate_pence_per_kwh": "25.50",
            },
            {
                "tariff_id": " unvalidated example ",
                "tariff_name": "",
                "supplier": "Example Energy",
                "fix_length_months": "banana",
                "exit_fee_pounds": "-50",
                "standing_charge_pence_per_day": " 48.00 ",
                "day_type": "FUNDAY",
                "start_time_local": "23:00",
                "end_time_local": "07:00",
                "unit_rate_pence_per_kwh": "not a number",
            },
        ),
    )


def test_writes_meter_readings_and_ingestion_metadata(
    tmp_path: Path, meter_batch: RawBatch
):
    database_path = tmp_path / "raw_source.duckdb"
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
                source_format,
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
                "fuse_csv",
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


def test_rolls_back_raw_rows_when_metadata_insert_fails(
    tmp_path: Path, meter_batch: RawBatch
):
    database_path = tmp_path / "raw_source.duckdb"
    import_id = UUID(int=1)
    ingested_at = datetime(2026, 9, 21, tzinfo=UTC)

    write_batch(
        database_path,
        meter_batch,
        import_id=import_id,
        source_sha256="original",
        ingested_at=ingested_at,
    )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        original_rows = connection.execute("""
            SELECT * FROM raw.meter_readings ORDER BY source_row_number
            """).fetchall()
        original_metadata = connection.execute("""
            SELECT * FROM raw.ingestion_files
            """).fetchall()

    # Raw rows allow repeated import IDs; metadata's primary key rejects them.
    with pytest.raises(duckdb.ConstraintException, match="Duplicate key"):
        write_batch(
            database_path,
            meter_batch,
            import_id=import_id,
            source_sha256="retry",
            ingested_at=ingested_at,
        )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        assert connection.execute("""
            SELECT * FROM raw.meter_readings ORDER BY source_row_number
            """).fetchall() == original_rows
        assert connection.execute("""
            SELECT * FROM raw.ingestion_files
            """).fetchall() == original_metadata


def test_writes_values_to_named_columns_with_reversed_headers(
    tmp_path: Path, meter_batch: RawBatch
):
    database_path = tmp_path / "raw_source.duckdb"
    reversed_headers = meter_batch.headers[::-1]
    batch = replace(
        meter_batch,
        headers=reversed_headers,
        rows=tuple(
            {header: row[header] for header in reversed_headers}
            for row in meter_batch.rows
        ),
    )

    write_batch(
        database_path,
        batch,
        import_id=UUID(int=1),
        source_sha256="abc123",
        ingested_at=datetime(2026, 9, 21, tzinfo=UTC),
    )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        raw_rows = connection.execute("""
            SELECT meter_id, interval_timestamp, energy_value, source_fields
            FROM raw.meter_readings
            ORDER BY source_row_number
            """).fetchall()

    assert raw_rows == [
        (
            row["meter_id"],
            row["interval_timestamp"],
            row["energy_value"],
            row["source_fields"],
        )
        for row in meter_batch.rows
    ]


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
def test_rejects_noncanonical_meter_headers(
    tmp_path: Path, meter_batch: RawBatch, headers, row
):
    database_path = tmp_path / "raw_source.duckdb"
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


def test_writes_tariffs_and_ingestion_metadata(tmp_path: Path, tariff_batch: RawBatch):
    database_path = tmp_path / "raw_source.duckdb"
    import_id = UUID("12345678-1234-5678-1234-567812345678")
    ingested_at = datetime(2026, 9, 21, 10, 30, tzinfo=UTC)

    write_batch(
        database_path,
        tariff_batch,
        import_id=import_id,
        source_sha256="tariff123",
        ingested_at=ingested_at,
    )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        raw_rows = connection.execute("""
            SELECT * FROM raw.tariffs ORDER BY source_row_number
            """).fetchall()
        ingestion_file = connection.execute("""
            SELECT import_id, source_format, source_kind, source_path, source_sha256,
                   row_count, ingested_at, timestamp_boundary, timestamp_timezone,
                   energy_unit, interval_duration_minutes
            FROM raw.ingestion_files
            """).fetchall()
        column_types = connection.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'raw' AND table_name = 'tariffs'
            ORDER BY ordinal_position
            """).fetchall()

    assert raw_rows == [
        (*[row[header] for header in TARIFF_RAW_HEADERS], import_id, number)
        for number, row in enumerate(tariff_batch.rows, start=1)
    ]
    assert ingestion_file == [
        (
            import_id,
            "tariff_csv",
            "tariff",
            "data/landing/tariffs/tariffs_example.csv",
            "tariff123",
            2,
            ingested_at,
            None,
            None,
            None,
            None,
        )
    ]
    assert column_types == [
        *[(header, "VARCHAR") for header in TARIFF_RAW_HEADERS],
        ("import_id", "UUID"),
        ("source_row_number", "BIGINT"),
    ]


@pytest.mark.parametrize("extra_header", [False, True], ids=["missing", "extra"])
def test_rejects_noncanonical_tariff_headers(
    tmp_path: Path, tariff_batch: RawBatch, extra_header: bool
):
    database_path = tmp_path / "raw_source.duckdb"
    row = dict(tariff_batch.rows[0])
    if extra_header:
        row["extra_column"] = "unexpected"
        message = r"missing=\[\], unexpected=\['extra_column'\]"
    else:
        del row["unit_rate_pence_per_kwh"]
        message = r"missing=\['unit_rate_pence_per_kwh'\], unexpected=\[\]"
    bad_batch = replace(tariff_batch, headers=tuple(row), rows=(row,))

    with pytest.raises(ValueError, match=message):
        write_batch(
            database_path,
            bad_batch,
            import_id=UUID(int=1),
            source_sha256="tariff123",
            ingested_at=datetime(2026, 9, 21, tzinfo=UTC),
        )

    assert not database_path.exists()


@pytest.mark.parametrize("empty_batch", [False, True], ids=["missing-value", "empty"])
def test_rejects_structurally_invalid_batch_before_creating_database(
    tmp_path: Path, meter_batch: RawBatch, empty_batch: bool
):
    database_path = tmp_path / "raw_source.duckdb"
    if empty_batch:
        bad_batch = replace(meter_batch, rows=())
        message = "at least one row"
    else:
        row = {**meter_batch.rows[0], "energy_value": None}
        bad_batch = replace(meter_batch, rows=(row,))
        message = "Row 1 has structurally missing values for: energy_value"

    with pytest.raises(ValueError, match=message):
        write_batch(
            database_path,
            bad_batch,
            import_id=UUID(int=1),
            source_sha256="abc123",
            ingested_at=datetime(2026, 9, 21, tzinfo=UTC),
        )

    assert not database_path.exists()


def test_appends_tariffs_alongside_meter_readings(
    tmp_path: Path, meter_batch: RawBatch, tariff_batch: RawBatch
):
    database_path = tmp_path / "raw_source.duckdb"
    for number, batch in enumerate((meter_batch, tariff_batch, tariff_batch), start=1):
        write_batch(
            database_path,
            batch,
            import_id=UUID(int=number),
            source_sha256=f"source{number}",
            ingested_at=datetime(2026, 9, 21, tzinfo=UTC),
        )

    with duckdb.connect(str(database_path), read_only=True) as connection:
        tariff_rows = connection.execute("""
            SELECT import_id, source_row_number FROM raw.tariffs
            ORDER BY import_id, source_row_number
            """).fetchall()
        meter_rows = connection.execute("""
            SELECT import_id, source_row_number FROM raw.meter_readings
            ORDER BY source_row_number
            """).fetchall()
        ingestion_files = connection.execute("""
            SELECT import_id, source_kind, row_count FROM raw.ingestion_files
            ORDER BY import_id
            """).fetchall()

    assert tariff_rows == [
        (UUID(int=2), 1),
        (UUID(int=2), 2),
        (UUID(int=3), 1),
        (UUID(int=3), 2),
    ]
    assert meter_rows == [(UUID(int=1), 1), (UUID(int=1), 2)]
    assert ingestion_files == [
        (UUID(int=1), "meter_readings", 2),
        (UUID(int=2), "tariff", 2),
        (UUID(int=3), "tariff", 2),
    ]
