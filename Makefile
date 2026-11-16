.PHONY: setup data train evaluate test lint type-check run dashboard compose-up compose-down load-test seed advisories

PY ?= python3

setup:            ## install runtime + dev deps
	pip install -r requirements-dev.txt

data:             ## download UCI SMS Spam Collection (optional)
	mkdir -p data/raw && cd data/raw && \
	curl -sLO https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip && \
	unzip -o smsspamcollection.zip

train: data        ## build dataset + train baseline model
	$(PY) data/scripts/build_dataset.py
	$(PY) -m scamshield.model --csv data/training/train.csv

evaluate:          ## golden-set evaluation (writes docs/results.md)
	PYTHONPATH=. $(PY) evaluation/evaluate.py

test:              ## run test suite with coverage
	$(PY) -m pytest --cov=scamshield --cov-report=term-missing

lint:              ## ruff lint + format check
	ruff check . && ruff format --check .

type-check:        ## mypy on the package
	mypy scamshield/

run:               ## serve the API locally
	uvicorn scamshield.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:         ## serve the Streamlit dashboard
	streamlit run dashboard/app.py --server.port 8501

seed:              ## load 90 days of demo analyses into the DB
	$(PY) scripts/seed_demo_data.py
	$(PY) automation/fetch_advisories.py --seed-if-empty

advisories:        ## fetch live advisories (RSS)
	$(PY) automation/fetch_advisories.py --online

load-test:         ## locust against a running server (host=http://localhost:8000)
	locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 10 -t 60s

compose-up:        ## full stack: api + dashboard + prometheus + grafana
	docker compose up --build

compose-down:
	docker compose down

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
