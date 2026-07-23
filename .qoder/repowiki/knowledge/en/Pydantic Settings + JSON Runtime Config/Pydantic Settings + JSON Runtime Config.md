---
kind: configuration_system
name: Pydantic Settings + JSON Runtime Config
category: configuration_system
scope:
    - '**'
source_files:
    - app/core/config.py
    - .env.example
    - app/main.py
    - frontend/src/app/core/config/app-config.loader.ts
    - frontend/src/app/core/config/app-config.model.ts
    - frontend/public/config/app-config.json
---

The repository uses a two-tier configuration system:

Backend (Python/FastAPI) - app/core/config.py defines a single Settings class backed by pydantic_settings.BaseSettings. It is the only source of truth for runtime configuration and is consumed via an @lru_cache-wrapped get_settings() singleton. All config values are typed with Pydantic v2 Field(...) validators and cross-field validation via a model_validator(mode="after").

Loading order (per SettingsConfigDict):
1. Environment variables prefixed with WORKPLACE_ (e.g. WORKPLACE_DATABASE_URL, WORKPLACE_AGENT_MODEL_API_KEY)
2. .env file in the project root
3. Python defaults declared on each field

There is no hierarchical merging, no YAML/JSON backend, and no secret manager integration - secrets are expected to arrive as environment variables. The environment field drives feature toggles (is_sandbox property) used throughout the app (e.g. enabling mock API routes).

Key domains covered:
- Database URLs and Nucleus SQL Server user directory connection
- OpenAI model provider settings (provider, endpoint, key, timeouts, retries, token limits)
- Agent run worker tuning (poll/lease/renew/heartbeat intervals)
- Action control rate limits and pagination caps
- Session cookie security flags

Consumption pattern: modules import from app.core.config import get_settings and call it at request or startup time; the cache ensures a single instance per process. Alembic migrations also read from this same Settings object (alembic/env.py).

Frontend (Angular) - A separate, lightweight runtime config lives in frontend/public/config/app-config.json and is loaded at bootstrap by frontend/src/app/core/config/app-config.loader.ts. The loader fetches the JSON at runtime, then validates it against a Zod schema defined in app-config.model.ts (strict shape, URL normalization, enum constraints). This file is served statically and contains only client-facing knobs such as apiBaseUrl, defaultOrganizationId, mockUserId, requestTimeoutMs, enableDebugViews, and streamTransport.

Conventions developers should follow:
- Add new backend settings as fields on app/core/config.py::Settings with explicit Field(...) bounds; keep all defaults non-secret so .env.example stays minimal.
- Prefix every new env var with WORKPLACE_; never hard-code env names elsewhere.
- Do not create additional BaseSettings subclasses - route everything through the single Settings class.
- For frontend-only runtime knobs, extend frontend/public/config/app-config.json and its Zod schema together; do not bake build-time constants into Angular code that should be configurable per deployment.
- Keep secrets out of version control - ship only .env.example with placeholder keys.