# Phase 0 acceptance

Baseline: `1863fc0ec62b148dc1976c154afa1f91e3375c16`

Phase 0 is complete when all of the following pass:

```bash
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
python -m compileall -q scripts tests
pytest -q
git diff --check
```

Acceptance assertions:

- The manifest contains exactly 31 unique method/path pairs.
- Every manifest route exists in FastAPI OpenAPI.
- Every declared request/response model matches the generated OpenAPI reference.
- Every authenticated route exposes `X-Mock-User-Id` as a header parameter.
- All JSON examples validate against current Pydantic models or the documented error/event envelope.
- The normalized UI event schema contains no raw-reasoning event type.
- Known missing interfaces are explicitly listed.
- No Angular runtime, visual shell, fake stream or placeholder workflow is added in Phase 0.
