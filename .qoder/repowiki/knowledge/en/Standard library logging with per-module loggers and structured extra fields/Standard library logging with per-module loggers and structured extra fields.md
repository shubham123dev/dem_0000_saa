---
kind: logging_system
name: Standard library logging with per-module loggers and structured extra fields
category: logging_system
scope:
    - '**'
source_files:
    - app/main.py
    - app/core/errors.py
    - app/agent/providers/workplace_openai_responses.py
    - app/services/agent_run_worker.py
    - alembic/env.py
---

The repository uses Python's built-in `logging` module exclusively — no third-party logging framework (loguru, structlog, etc.) is configured. Logging is set up ad-hoc in each module that needs it by calling `logging.getLogger(<name>)`, producing one logger per logical subsystem rather than a single global logger.

**What system/approach is used**
- Standard-library `logging` only.
- No centralized configuration file or `logging.config.dictConfig` call at application startup; handlers/filters are left to the default root logger unless overridden externally (e.g. via `LOGGING_CONFIG` environment variable).
- Alembic migrations explicitly load a config file via `from logging.config import fileConfig` when `alembic.ini` is present, so migration output can be tuned separately from the app process.

**Key files and packages**
- `app/main.py` — creates the FastAPI app and logs startup diagnostics against the `uvicorn` logger.
- `app/core/errors.py` — defines the app-wide exception hierarchy and registers FastAPI exception handlers; the unhandled-exception handler logs stack traces via `logger.exception(...)` on the `app.errors` logger.
- `app/agent/providers/workplace_openai_responses.py` — logs planner validation rejections under `app.agent_model` using structured `extra=` dicts.
- `app/services/agent_run_worker.py` — logs agent-run lifecycle events (`debug`, `exception`) under `app.agent_runs`.
- `alembic/env.py` — bridges Alembic into the same `logging.config.fileConfig` mechanism as `alembic.ini`.

**Architecture and conventions**
- **Logger naming**: Each module declares a module-level `logger = logging.getLogger("<domain>")` following a dotted namespace convention: `app.errors`, `app.agent_model`, `app.agent_runs`, plus the external `uvicorn` logger for server-level messages.
- **Structured fields**: Business-contextual data is attached through the `extra=` keyword argument (e.g. `run_id`, `conversation_id`, `planner_validation_reason`, `provider_response_id`, `model`, `function_names`). This makes logs machine-parseable without changing the formatter.
- **Request correlation**: The HTTP middleware injects an `X-Request-Id` header into every request/response, and the error handler surfaces it in JSON responses. While the middleware does not automatically propagate the ID into log records, the pattern establishes a cross-cutting correlation token that structured log fields can reference.
- **Level usage**: `info` for notable state transitions (startup, rejected planner outputs), `debug` for non-critical operational noise (auto-title skip), `exception` for unexpected failures (run executor, coordinator loop, unhandled exceptions).
- **No dedicated logging layer**: There is no wrapper class or context manager around `logging`; modules call the logger directly.

**Rules developers should follow**
1. Use `logging.getLogger("app.<subsystem>")` at module top-of-file to obtain a logger scoped to your feature area.
2. Attach contextual identifiers via `extra={...}` (e.g. `run_id`, `conversation_id`, `action_id`) instead of string interpolation, so downstream sinks can index/filter on them.
3. Prefer `logger.exception(...)` inside `except Exception:` blocks so the traceback is emitted automatically.
4. Keep message text human-readable and move variable payloads into `extra`.
5. Do not configure handlers/formatters in individual modules — rely on the process-level configuration (or `alembic.ini` for migrations) to control output format and destination.