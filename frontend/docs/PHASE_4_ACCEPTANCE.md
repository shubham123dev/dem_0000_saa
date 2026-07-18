# Phase 4 acceptance

- Ask AI sends requests only through `WorkplaceAgentApiService.query`.
- Read, clarification, and action-proposal modes render correctly.
- No raw evidence ID, tool name, proposal ID, organization ID, or actor ID is displayed or stored.
- Clarification replies include visible original-request context and remain within 4,000 characters.
- Conversation history is current-tab `sessionStorage`, not fake server persistence.
- Enter sends, Shift+Enter inserts a line, and the composer enforces backend limits.
- Pending requests can stop browser waiting without claiming server cancellation.
- No automatic retry, fake streaming, fake planning stage, or raw chain-of-thought exists.
- Proposal cards navigate to Pending approvals and do not approve or execute.
- Strict TypeScript, Angular templates, ESLint, Vitest, production build, Playwright, Phase 0–4 validators, and the complete backend suite pass.
