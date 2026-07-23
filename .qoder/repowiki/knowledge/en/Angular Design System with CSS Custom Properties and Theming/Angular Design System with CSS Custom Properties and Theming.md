---
kind: frontend_style
name: Angular Design System with CSS Custom Properties and Theming
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/src/styles/_tokens.scss
    - frontend/src/styles/_themes.scss
    - frontend/src/styles/_reset.scss
    - frontend/src/styles/_patterns.scss
    - frontend/src/styles.scss
    - frontend/src/app/shared/theme/ui-theme.service.ts
    - frontend/src/app/shared/ui/ui-button/ui-button.component.scss
    - frontend/src/app/shared/ui/ui-badge/ui-badge.component.scss
    - frontend/angular.json
---

The frontend uses an Angular application built with SCSS, organized around a token-driven design system that relies entirely on CSS custom properties (CSS variables) for visual consistency. There is no external UI component library — the project ships its own small set of shared primitives under `src/app/shared/ui/` (button, badge, callout, input, textarea, spinner, skeleton, surface, icon-button, status-indicator, action-surface). These primitives are composed into feature components in `src/app/features/` (approval-center, assistant-conversation, conversation-list, landing).

**Design tokens and theming**
- Tokens are declared as CSS custom properties in `src/styles/_tokens.scss`, covering typography (`--ui-text-*`, `--ui-font-*`), spacing (`--ui-space-*`), radii (`--ui-radius-*`), control sizes (`--ui-control-*`), colors (brand, neutral, semantic blue/green/amber/red scales), surfaces, borders, shadows, durations/easings, z-indexes, and shell layout constants.
- Theme overrides live in `src/styles/_themes.scss`, which switches variable values based on `html[data-theme='dark']` / `html[data-theme='light']`. A `prefers-contrast: more` media query and `forced-colors: active` block provide high-contrast/accessibility variants.
- The `UiThemeService` (`src/app/shared/theme/ui-theme.service.ts`) persists a preference (`system | light | dark`) to localStorage, resolves against `prefers-color-scheme`, and writes `data-theme` + `data-themePreference` attributes onto `<html>` plus `colorScheme` style, so all tokens reactively switch at runtime.

**SCSS methodology**
- Global entrypoint `src/styles.scss` imports the token/theme/reset/accessibility/patterns partials via `@use`, keeping global styles isolated from component-scoped styles.
- Component styles use BEM-like class names prefixed with `ui-` (e.g., `.ui-button`, `.ui-badge`, `.ui-callout`) and modifier suffixes (`--primary`, `--secondary`, `--small`, `--danger`, etc.). Components scope their rules inside `:host` or element selectors; they never import global files directly, relying instead on the root stylesheet to expose tokens.
- Shared layout patterns (`ui-stack`, `ui-cluster`, `ui-dot-grid`) live in `_patterns.scss` for reuse across features.

**Build and conventions**
- `angular.json` sets default schematics to generate components with `style: 'scss'` and `changeDetection: 'OnPush'`, and compiles inline SCSS (`inlineStyleLanguage: 'scss'`). Production budgets cap initial bundle at 600 kB warning / 900 kB error and per-component styles at 8 kB / 12 kB.
- No Tailwind, Bootstrap, or other utility-first framework is present; styling is hand-authored SCSS driven by tokens.
- Responsive behavior is achieved through CSS media queries and clamp-based fluid typography rather than a breakpoint grid.