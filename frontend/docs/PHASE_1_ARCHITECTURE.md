# Phase 1 Angular architecture

Phase 1 creates a native Angular 21 LTS application using standalone components, strict TypeScript, zoneless change detection, Signals for local identity state, RxJS for HTTP flows, Zod at every network boundary, Vitest, and Playwright.

## Boundary rules

1. `WorkplaceAgentApiService` is the only feature-facing backend facade.
2. `ValidatedHttpService` is the only class allowed to inject `HttpClient`.
3. Components never know endpoint strings.
4. Functional interceptors own request IDs, sandbox identity, and error conversion.
5. Runtime configuration is fetched and validated before Angular bootstraps.
6. No risk, approval, organization-scope, or execution decision is calculated in the browser.
7. Streaming remains explicitly unavailable; Phase 1 does not simulate it.

## Version choice

Angular 21 LTS is selected instead of Angular 22 because it supports Node 20.19, 22.12, and 24 while retaining modern standalone, zoneless and Vitest defaults. Dependencies are exact-pinned; `npm install` creates the lockfile in the target repository.


## Browser-to-backend routing

Runtime configuration uses the same-origin `/api` prefix. The development
server proxy forwards that prefix to FastAPI and strips it. Deployment must
provide an equivalent reverse proxy. Components never display the API base URL
or individual endpoint paths.
