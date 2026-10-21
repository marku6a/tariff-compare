from datetime import datetime, UTC
from pathlib import Path
from uuid import UUID

import duckdb
import pyarrow as pa

from ingestion.models import RawBatch
from ingestion.validation import validate_batch
from ingestion.raw_schema import METER_READINGS_RAW_HEADERS, TARIFF_RAW_HEADERS


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
        expected_headers = TARIFF_RAW_HEADERS
        target_table = "raw.tariffs"
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
            source_format VARCHAR,
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
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw.tariffs (
            tariff_id VARCHAR,
            tariff_name VARCHAR,
            supplier VARCHAR,
            fix_length_months VARCHAR,
            exit_fee_pounds VARCHAR,
            standing_charge_pence_per_day VARCHAR,
            day_type VARCHAR,
            start_time_local VARCHAR,
            end_time_local VARCHAR,
            unit_rate_pence_per_kwh VARCHAR,
            import_id UUID,
            source_row_number BIGINT)
            """)

    with duckdb.connect(database_path) as con:
        ensure_raw_tables(con)

        # prepare batch and metadata
        source_columns = ", ".join(expected_headers)
        raw_rows_sql = f"""
                    INSERT INTO {target_table}
                        ({source_columns}, import_id, source_row_number)
                    SELECT {source_columns}, ?::UUID, source_row_number
                    FROM pa_table
                    """
        raw_rows_params = [str(import_id)]

        metadata_sql = f"""
                    INSERT INTO raw.ingestion_files (
                        import_id,
                        source_format,
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
                    """
        meter_metadata = batch.meter_metadata
        metadata_params = [
            str(import_id),
            batch.source_format,
            batch.source_kind,
            str(batch.source_path),
            source_sha256,
            pa_table.num_rows,
            meter_metadata.timestamp_boundary if meter_metadata is not None else None,
            meter_metadata.timestamp_timezone if meter_metadata is not None else None,
            meter_metadata.energy_unit if meter_metadata is not None else None,
            (
                meter_metadata.interval_duration_minutes
                if meter_metadata is not None
                else None
            ),
            ingested_at,
        ]

        # insert batch and metadata atomically
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(raw_rows_sql, raw_rows_params)
            con.execute(metadata_sql, metadata_params)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
