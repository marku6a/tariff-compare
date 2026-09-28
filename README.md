# Tariff Compare

A local batch pipeline for comparing electricity-tariff costs.

## Architecture

`CSV files → Python ingestion → raw.duckdb → dbt → analytics.duckdb → Superset`

Python is intentionally limited to landing files and recording ingestion metadata.
dbt attaches the raw database read-only, performs validation and transformations,
and writes dashboard-ready models to the analytics database.

## Layout

- `data/landing/meter_readings/` — electricity-usage CSV files awaiting ingestion.
- `data/landing/tariffs/` — manually entered tariff CSV files awaiting ingestion.
- `data/processed/` — successfully landed source files.
- `data/contracts/` — input data contracts for manually maintained files.
- `data/templates/` — copyable CSV templates; do not place these in `landing/`.
- `warehouse/` — local DuckDB database files (ignored by Git).
- `src/ingestion/` — installable, thin ingestion application.
- `dbt/` — validation and transformation project.
- `superset/` — local Superset container configuration.
- `tests/` — Python ingestion tests.

## Intended commands

```bash
make ingest
make validate
make transform
make pipeline
make dashboard
```

See `dbt/profiles.yml.example` for the intended read-only raw-database attachment.
See `data/contracts/tariff_csv.md` for the manually entered tariff CSV contract.

## Python ingestion boundary

The Python application selects a source provider, checks that a file is
structurally recognised, maps provider column names to stable raw column names,
and loads source values into `raw.duckdb` with ingestion metadata. Meter-reading
providers output `meter_id`, `interval_timestamp`, `energy_value`,
the timestamp boundary and time zone, the energy unit, interval duration and a JSON string of
provider-only values in `source_fields`.
dbt parses timestamps and numbers, places readings on a common interval boundary, converts units, and applies validation
and tariff-cost rules. The processed file archive will retain the
original CSV header names and file contents.

The package uses a `src/` layout and can be invoked with
`uv run python -m ingestion.cli`. Provider adapters live in
`src/ingestion/providers/`; add a new adapter when a different source export
format arrives.
