from datetime import datetime, UTC
from pathlib import Path
from uuid import UUID

import duckdb
import pyarrow as pa

from ingestion.models import RawBatch
from ingestion.validation import validate_batch
from ingestion.raw_schema import METER_READINGS_RAW_HEADERS


def write_batch(
    database_path: Path,
    batch: RawBatch,
    *,
    import_id: UUID,
    source_sha256: str,
    ingested_at: datetime,
) -> None:
    # check non-zero rows and structurally missing values
    validate_batch(batch)

    # check canonical headers
    if batch.source_kind == "meter_readings":
        expected_headers = METER_READINGS_RAW_HEADERS
        target_table = "raw.meter_readings"
    elif batch.source_kind == "tariff":
        # Later: select TARIFF_RAW_HEADERS and raw.tariffs here.
        raise NotImplementedError("Tariff writing is not implemented yet")
    else:
        raise ValueError(f"Unsupported source kind: {batch.source_kind}")

    missing = set(expected_headers) - set(batch.headers)
    unexpected = set(batch.headers) - set(expected_headers)
    if missing or unexpected:
        raise ValueError(
            f"Batch does not match raw schema: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    # construct pyarrow table
    # use expected_headers to maintain header order
    pa_schema = pa.schema(
        [pa.field(header, pa.string()) for header in expected_headers]
        + [pa.field("source_row_number", pa.int64())]
    )

    pa_rows = [
        {
            **{header: row[header] for header in expected_headers},
            "source_row_number": number,
        }
        for number, row in enumerate(batch.rows, start=1)
    ]

    pa_table = pa.Table.from_pylist(pa_rows, schema=pa_schema)

    # create tables helper
    def ensure_raw_tables(con):
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.ingestion_files (
            import_id UUID PRIMARY KEY,
            provider VARCHAR,
            source_kind VARCHAR,
            source_path VARCHAR,
            source_sha256 VARCHAR,
            row_count BIGINT,
            timestamp_boundary VARCHAR,
            timestamp_timezone VARCHAR,
            energy_unit VARCHAR,
            interval_duration_minutes BIGINT,
            ingested_at TIMESTAMPTZ)
            """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.meter_readings (
            meter_id VARCHAR,
            interval_timestamp VARCHAR,
            energy_value VARCHAR,
            source_fields VARCHAR,
            import_id UUID,
            source_row_number BIGINT)
            """)
        # add tariff check later

    # Add raw.tariffs here when its contract is ready.

    with duckdb.connect(database_path) as con:
        ensure_raw_tables(con)

        # insert batch data
        source_columns = ", ".join(expected_headers)
        con.execute(
            f"""
            INSERT INTO {target_table}
                ({source_columns}, import_id, source_row_number)
            SELECT {source_columns}, ?::UUID, source_row_number
            FROM pa_table
            """,
            [str(import_id)],
        )

        # insert ingestion file data
        con.execute(
            f"""
            INSERT INTO raw.ingestion_files (
                import_id,
                provider,
                source_kind,
                source_path,
                source_sha256,
                row_count,
                timestamp_boundary,
                timestamp_timezone,
                energy_unit,
                interval_duration_minutes,
                ingested_at)
            VALUES (?::UUID, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(import_id),
                batch.provider,
                batch.source_kind,
                str(batch.source_path),
                source_sha256,
                pa_table.num_rows,
                batch.timestamp_boundary,
                batch.timestamp_timezone,
                batch.energy_unit,
                batch.interval_duration_minutes,
                ingested_at,
            ],
        )
