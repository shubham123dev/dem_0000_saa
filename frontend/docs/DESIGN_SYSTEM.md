# Angular workplace-agent design system

Phase 2 established the visual contract, and the Phase 3 hardening pass closes the remaining accessibility and product-exposure gaps.

## Principles

- Semantic CSS custom properties are the only source of product color, spacing, radius, shadow, typography, and motion.
- Light and dark themes change semantic values, not component rules.
- Theme preference is applied before Angular bootstrap to prevent a light-theme flash.
- Components use `ChangeDetectionStrategy.OnPush` and expose native accessibility semantics.
- Status colors are never the only indicator; labels remain visible and light-theme text/background pairs meet the normal-text contrast target.
- Input and textarea primitives implement `ControlValueAccessor` for reactive and template-driven forms.
- Clickable cards use the native-button `UiActionSurface`; presentational `UiSurface` never pretends to be interactive.
- The UI does not expose API routes, model prompts, SQL, internal actor IDs, organization IDs, or backend-owned policy calculations.

## Included primitives

`UiActionSurface`, `UiButton`, `UiIconButton`, `UiBadge`, `UiSurface`, `UiCallout`, `UiStatusIndicator`, `UiInput`, `UiTextarea`, `UiSpinner`, and `UiSkeleton`.

## Theme contract

`UiThemeService` supports `system`, `light`, and `dark`. Explicit choices persist in local storage. System mode follows `prefers-color-scheme`. The pre-bootstrap initializer and Angular service use the same storage key and document attributes.

## Styling rule

Component SCSS must use semantic variables such as `--ui-surface-base` or `--ui-status-danger-fg`. New hexadecimal values belong only in `_tokens.scss` or `_themes.scss`.
