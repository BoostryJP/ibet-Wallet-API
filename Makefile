.PHONY: format isort black test run

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

test:
	pytest tests/ ${ARG}

test_migrations:
	poetry run pytest -vv --test-alembic -m "alembic"

run:
	gunicorn --worker-class server.AppUvicornWorker app.main:app
