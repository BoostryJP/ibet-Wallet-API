.PHONY: format isort black doc test test_migrations run

install:
	poetry install --no-root -E ibet-explorer
	poetry run pre-commit install

update:
	poetry update

format: isort black

isort:
	isort .

black:
	black .

doc:
	poetry run python docs/generate_openapi_doc.py

test:
	pytest tests/ ${ARG}

test_migrations:
	poetry run pytest -vv --test-alembic -m "alembic"

run:
	gunicorn --worker-class server.AppUvicornWorker app.main:app
