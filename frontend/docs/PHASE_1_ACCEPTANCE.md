# Phase 1 acceptance

Phase 1 is complete when:

- `npm install` succeeds and creates `package-lock.json`.
- `npm run validate:phase1` passes.
- the Angular production build respects bundle budgets.
- all 31 backend operations are represented by one facade.
- runtime configuration rejects unknown or malformed fields.
- success and error payloads are validated at runtime.
- no component or feature service issues raw HTTP requests.
- mock identity and request IDs are attached by functional interceptors.
- Vitest unit tests and Playwright test discovery pass.
- the placeholder shell works at desktop and compact widths.
- no fake stream, fake reasoning, or fake execution behavior exists.
