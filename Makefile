.PHONY: format lint typecheck doc test test_guardrail_check test_guardrail test_migrations run

install:
	UV_MALWARE_CHECK=1 uv sync --frozen --no-install-project --all-extras
	uv run pre-commit install

update:
	uv lock --upgrade

format:
	uv run ruff format && uv run ruff check --fix --select I

lint:
	uv run ruff check --fix

typecheck:
	uv run pyright --project pyrightconfig.json

doc:
	uv run python docs/generate_openapi_doc.py

test:
	uv run pytest tests/ ${ARG}

test_guardrail_check:
	uv run pytest --override-ini addopts='' --noconftest -v -m "guardrail_check" tests/test_guardrail_check.py

test_guardrail: test_guardrail_check

test_migrations:
	uv run pytest -vv --test-alembic -m "alembic"

run:
	uv run gunicorn --worker-class server.AppUvicornWorker app.main:app
