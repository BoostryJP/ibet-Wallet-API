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

run:
	gunicorn --worker-class server.AppUvicornWorker app.main:app
