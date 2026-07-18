# Frontend validation

```bash
cd frontend
npm install
npm run validate:phase1
npx playwright install chromium
npm run e2e
```

`validate:phase1` runs architecture-boundary checks, strict application and test type checks, Angular-aware ESLint, Vitest, a production build, and Playwright test discovery. Browser installation is kept explicit because Playwright browser binaries are platform-specific.
