.PHONY: ingest validate transform pipeline dashboard test

ingest:
	python -m python.ingest

validate:
	cd dbt && dbt build --select path:models/staging,path:models/validation

transform:
	cd dbt && dbt build --select path:models/intermediate,path:models/marts

pipeline: ingest validate transform

dashboard:
	docker compose -f superset/docker-compose.yml up --build

test:
	pytest
