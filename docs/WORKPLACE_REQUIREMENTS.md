# Workplace Agent — Requirements (Step 0)

## Relationship to the existing chatbot

- The existing **SARA/chatbot** repository remains **separate and unchanged**.
- This Workplace Agent is a **separate backend/product area** with its own
  repository, data model, and lifecycle.
- Step 0 does **not** integrate with `/ai-search_1`, does not reuse chatbot
  pipelines, and does not alter any current chatbot behavior.

## Users and environment

- The initial users are **internal employees**.
- The **initial environment is sandbox only**. Production access is explicitly
  **out of scope** and is actively blocked by the backend.

## Current state of Nucleus data

- Real Nucleus pages currently rely on a **frontend/`sessionStorage` prototype**
  for data.
- Real **Nucleus organization APIs are not yet available**.
- Step 0 therefore provides a **mock database** and a **mock adapter** that
  stands in for the future Nucleus organization API.

## What Step 0 delivers

Step 0 proves exactly one flow:

```
Mock internal employee
→ authenticated mock context (X-Mock-Employee-Id)
→ sandbox organization selected
→ employee permission checked
→ organization profile read from mock database
→ exact state returned
→ read event recorded in audit log
```

## Explicit non-goals for Step 0

- No LLM planner, no chain-of-thought logic, no OpenAI/LLM SDK.
- No write actions, approval flows, or execution of proposed changes.
- No arbitrary SQL, arbitrary HTTP/URL execution, shell tools, or browser
  automation.
- No production integration, production credentials, or real employee data.
- No frontend code, billing features, API-key creation, or security-policy
  modification.

## Guardrails

- Permissions are **backend-owned** and read from the database. Authorization
  is never taken from the request body or user text.
- The service and API layers depend on an **organization adapter contract**,
  not on the SQLite ORM.
- Audit events are **append-only**.
- API responses never leak stack traces, database paths, SQL, or secrets.
