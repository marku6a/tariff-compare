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
- `python/` — thin ingestion application.
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
