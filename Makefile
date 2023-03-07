.PHONY: isort black test

format: isort black

isort:
	isort .

black:
	black .

test:
	pytest tests/
