# Phase 2 acceptance

Phase 2 is complete when:

- the current commit is the validated Phase 1 v2 baseline;
- `python scripts/validate_angular_phase2.py --repo .` passes;
- strict TypeScript and Angular template checking pass;
- Angular-aware ESLint reports zero errors;
- every Vitest suite passes;
- the production build remains inside budgets;
- Playwright discovers and runs the showcase and theme-persistence tests;
- ten primitives render from semantic tokens;
- system, light, and dark preferences work and persist;
- forced-colors and reduced-motion fallbacks exist;
- no raw API URL, fake stream, fake reasoning stage, proposal execution, or backend policy calculation is introduced.
