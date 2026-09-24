# ibet-Wallet-API

## Start here

- This is a Python 3.14 FastAPI service backed by PostgreSQL or MySQL and an ibet-compatible Ethereum RPC node.
- Use `uv` and the root [Makefile](Makefile) for development commands. Do not introduce a second package manager or command convention.
- Read the [README](README.md) for setup and runtime prerequisites, [ENV_LIST.md](ENV_LIST.md) for configuration, and [migrations/README.md](migrations/README.md) before changing database schema or migration behavior.
- Keep changes focused on the owning module, preserve existing public API contracts, and add or update the nearest matching tests.
- When creating source code, copy the copyright and Apache 2.0 license header from a neighboring file in the same language. Preserve the existing copyright holder and wording; do not invent a new header or year.
- Generated or substantially changed code must include concise English comments that improve readability by explaining module responsibility, intent, or complex operations, matching the surrounding code. Comments may restate code when that makes the behavior easier to understand; avoid noisy comments on trivial lines.

## Commands

Run these from the repository root:

| Purpose | Command |
| --- | --- |
| Install dependencies and hooks | `make install` |
| Format Python and sort imports | `make format` |
| Run Ruff checks | `make lint` |
| Run strict Pyright checks | `make typecheck` |
| Run the default test suite | `UNIT_TEST_MODE=1 RESPONSE_VALIDATION_MODE=1 make test` |
| Run a focused test selection | `make test ARG="-k test_name"` |
| Run repository guardrails | `make test_guardrail_check` |
| Run migration tests | `make test_migrations` |
| Regenerate the OpenAPI document | `make doc` |
| Run the API server | `make run` |

The default pytest configuration excludes migration and guardrail tests; run their dedicated targets when relevant. Tests and local runtime flows need the database and blockchain services described in [docker-compose.yml](docker-compose.yml). Batch processes use [bin/run_indexer.sh](bin/run_indexer.sh) and [bin/run_processor.sh](bin/run_processor.sh).

## Architecture

- [app/main.py](app/main.py) creates the FastAPI application, registers routers and middleware, and maps application exceptions to responses.
- [app/api/routers](app/api/routers) owns HTTP endpoints. Keep endpoint-specific query and response behavior close to its domain router.
- [app/model/db](app/model/db) contains SQLAlchemy models; [app/model/schema](app/model/schema) contains Pydantic request and response schemas; [app/model/type](app/model/type) contains shared types.
- [app/database](app/database) owns shared synchronous and asynchronous engines, pools, and session factories. [app/contracts](app/contracts) and [app/utils/web3_utils.py](app/utils/web3_utils.py) own contract access and RPC provider behavior.
- [batch](batch) contains blockchain indexers and database-backed processors. Indexers populate state and processors consume it for notifications, mail, or webhooks.
- [tests](tests) contains API, database, batch, migration, and contract-helper tests. Shared fixtures and Anvil synchronization live in [tests/conftest.py](tests/conftest.py) and [tests/helpers](tests/helpers).

## Project-specific guidance

- Match the surrounding async or sync boundary. Use the existing database dependency aliases and session factories instead of creating ad hoc sessions in routers or batch jobs.
- Reuse `AsyncContract` and `AsyncWeb3Wrapper` for asynchronous contract and RPC access. The custom provider/session behavior in [app/utils/web3_utils.py](app/utils/web3_utils.py) preserves RPC failover and HTTP keep-alive; bypassing it can regress RPC-heavy paths.
- Close sessions in all paths and dispose any short-lived SQLAlchemy engine that you create. Repeated contract transactions and batch tests are sensitive to leaked database clients.
- For tests that send transactions directly, follow the helpers and Anvil synchronization patch in [tests/conftest.py](tests/conftest.py); do not assume a newly created Web3 instance is covered automatically.
- Use the existing `AppError` hierarchy for API-visible application errors and keep response models aligned with the route contract. When endpoint schemas change, run `make doc` to update [docs/ibet_wallet_api.yaml](docs/ibet_wallet_api.yaml).
- For schema, index, or constraint changes, update the SQLAlchemy model and matching Alembic migration together, then run `make test_migrations` and follow the [migration guide](migrations/README.md). Do not edit generated OpenAPI output by hand.
- For database performance work, inspect both query shape and supporting indexes, and verify the change with focused API tests rather than assuming an index alone removes aggregation or join costs.
- Preserve repository supply-chain guardrails: Docker and Compose images are digest-pinned and remote pipe-to-shell installers are disallowed. Run `make test_guardrail_check` when changing dependency, Docker, Compose, or CI configuration.
