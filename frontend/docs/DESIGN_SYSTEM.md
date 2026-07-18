# Angular workplace-agent design system

Phase 2 establishes the visual contract used by every later UI phase.

## Principles

- Semantic CSS custom properties are the only source of product color, spacing, radius, shadow, typography, and motion.
- Light and dark themes change semantic values, not component rules.
- Components use `ChangeDetectionStrategy.OnPush` and expose native accessibility semantics.
- Status colors are never the only indicator; labels remain visible.
- Loading controls disable repeated activation and expose `aria-busy` or `role=status`.
- The UI does not expose API routes, model prompts, SQL, actor IDs, or backend-owned policy calculations.

## Included primitives

`UiButton`, `UiIconButton`, `UiBadge`, `UiSurface`, `UiCallout`, `UiStatusIndicator`, `UiInput`, `UiTextarea`, `UiSpinner`, and `UiSkeleton`.

## Theme contract

`UiThemeService` supports `system`, `light`, and `dark`. Explicit choices persist in local storage. System mode follows `prefers-color-scheme`. The resolved theme is written to `html[data-theme]`, while the chosen preference is written to `html[data-theme-preference]`.

## Styling rule

Component SCSS must use semantic variables such as `--ui-surface-base` or `--ui-status-danger-fg`. New hexadecimal values belong only in `_tokens.scss` or `_themes.scss`.
