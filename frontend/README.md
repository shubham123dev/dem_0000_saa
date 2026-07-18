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
