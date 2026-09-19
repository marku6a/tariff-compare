.PHONY: ingest validate transform pipeline dashboard test

ingest:
	uv run python -m ingestion.cli

validate:
	cd dbt && dbt build --select path:models/staging,path:models/validation

transform:
	cd dbt && dbt build --select path:models/intermediate,path:models/marts

pipeline: ingest validate transform

dashboard:
	docker compose -f superset/docker-compose.yml up --build

test:
	uv run pytest
