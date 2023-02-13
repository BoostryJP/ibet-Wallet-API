.PHONY: isort black test run

format: isort black

isort:
	isort src/.

black:
	poetry run black src

test:
	pytest .

dev:
	TEXTUAL=devtools poetry run python src/main.py

run:
	poetry run python src/main.py