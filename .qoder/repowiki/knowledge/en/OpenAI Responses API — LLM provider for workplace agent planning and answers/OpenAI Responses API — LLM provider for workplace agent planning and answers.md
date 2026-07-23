---
kind: external_dependency
name: OpenAI Responses API — LLM provider for workplace agent planning and answers
slug: openai
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

### Identity + role
- Vendor: OpenAI (Responses API at `https://api.openai.com/v1/responses`).
- Role: Optional LLM backend used by the workplace agent to produce plans (tool/action selection) and grounded answers from evidence.

### Integration points
- Provider class `OpenAIResponsesAgentModelGateway` in `app/agent/providers/openai_responses.py` posts JSON payloads with `json_schema` strict formatting and parses `output[].content[].text` back into typed plan/answer objects.
- Configured via `WORKPLACE_AGENT_MODEL_*` env vars (`provider`, `api_key`, `name`, `endpoint`, timeouts, retries, max output tokens); defaults point at OpenAI.
- Registered as the sole gateway in `app/agent/providers/__init__.py`.

### Usage model / constraints
- Calls are idempotent only at the HTTP layer; the gateway retries on 408/409/429/5xx with a fixed delay up to `maximum_attempts`. Non-retryable errors raise immediately.
- Authentication is Bearer token injected via `Authorization` header; the key comes from `WORKPLACE_AGENT_MODEL_API_KEY` and is never persisted in code.
- When `WORKPLACE_AGENT_MODEL_API_KEY` is empty (default `.env`), chat planning falls back to mock paths — the rest of the app (migrations, seeds, approval flows, UI) works without it.

### Migration status
- Currently wired to OpenAI Responses; the `providers` package exposes a single gateway class so swapping providers later is a dependency-injection change rather than a route-level refactor.

Verify exact request/response schema against the official OpenAI Responses API docs.