.PHONY: format isort black test run

format: isort black

isort:
	isort .

black:
	black .

test:
	pytest tests/

run:
	gunicorn --worker-class server.AppUvicornWorker app.main:app
