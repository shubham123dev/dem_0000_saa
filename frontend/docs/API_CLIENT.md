# Angular API client

`WorkplaceAgentApiService` covers all 31 endpoint method/path pairs recorded in Phase 0: health, readiness, capabilities, organization reads, Nucleus reads, generic resource reads, natural-language query, and the governed proposal lifecycle.

All incoming payloads are parsed through Zod. Invalid success payloads fail closed before reaching components. The API error interceptor converts the backend envelope into `WorkplaceApiError`, preserving `X-Request-Id` correlation.

The mock user is read from runtime configuration by `CurrentUserStore` and attached only to requests whose URL begins with the configured API base URL.
