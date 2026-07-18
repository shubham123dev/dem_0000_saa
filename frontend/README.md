# Angular frontend contract workspace

Phase 0 intentionally contains contracts and validation only. The Angular application is created after these interfaces are accepted.

- `docs/BACKEND_API_CONTRACT.md`: exact current FastAPI surface.
- `docs/AGENT_EVENT_CONTRACT.md`: planned safe Angular event envelope.
- `docs/ERROR_CONTRACT.md`: current error wire format and future UI normalization.
- `docs/PHASE_0_GAPS.md`: interfaces that do not exist yet.
- `contracts/api-manifest.json`: machine-readable route inventory.
- `contracts/ui-event.schema.json`: planned normalized UI-event schema.
- `contracts/examples/`: valid example payloads.

Validate from repository root:

```bash
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
```

<!-- ANGULAR_FRONTEND_PHASE_1_FOUNDATION -->
## Phase 1 Angular foundation

The repository now contains a strict Angular 21 LTS application, a runtime
configuration bootstrap, functional request/auth/error interceptors, Zod
validation for the current backend wire contracts, and a single typed facade
covering all 31 Phase 0 endpoint method/path pairs.

```bash
cd frontend
npm install
npm run validate:phase1
npx playwright install chromium
npm run e2e
```

The current shell is intentionally structural. Cloudflare-style visual tokens
and reusable controls are implemented in Phase 2; full dashboard and Ask AI
experiences follow in later phases.


### Local API routing

The browser uses the same-origin `/api` prefix. `npm start` loads
`proxy.conf.json`, forwards `/api/*` to the local FastAPI server at
`http://127.0.0.1:8000`, and removes the prefix. Production must provide the
same reverse-proxy contract. This avoids exposing endpoint infrastructure in the
non-technical UI and avoids cross-origin custom-header failures.
