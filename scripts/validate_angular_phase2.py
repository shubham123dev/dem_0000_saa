#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_HEAD = 'a714cd1167c50128303316ca4a7773d935c48685'
COMPONENTS = (
    'ui-badge',
    'ui-button',
    'ui-callout',
    'ui-icon-button',
    'ui-input',
    'ui-skeleton',
    'ui-spinner',
    'ui-status-indicator',
    'ui-surface',
    'ui-textarea',
)
TOKEN_FILES = ('_tokens.scss', '_themes.scss', '_reset.scss', '_accessibility.scss', '_patterns.scss')
HEX_PATTERN = re.compile(r'#[0-9a-fA-F]{3,8}\b')


def validate(repo: Path) -> list[str]:
    errors: list[str] = []
    frontend = repo / 'frontend'
    package = json.loads((frontend / 'package.json').read_text(encoding='utf-8'))
    if 'validate:phase2' not in package.get('scripts', {}):
        errors.append('frontend/package.json: validate:phase2 script is missing')

    styles = frontend / 'src/styles'
    for filename in TOKEN_FILES:
        if not (styles / filename).is_file():
            errors.append(f'frontend/src/styles/{filename}: missing')

    token_text = (styles / '_tokens.scss').read_text(encoding='utf-8')
    for token in (
        '--ui-brand-500',
        '--ui-surface-base',
        '--ui-text-primary',
        '--ui-border-focus',
        '--ui-status-danger-fg',
        '--ui-duration-panel',
    ):
        if token not in token_text:
            errors.append(f'_tokens.scss: missing {token}')

    theme_text = (styles / '_themes.scss').read_text(encoding='utf-8')
    if "html[data-theme='dark']" not in theme_text:
        errors.append('_themes.scss: dark theme selector is missing')
    if '@media (forced-colors: active)' not in theme_text:
        errors.append('_themes.scss: forced-colors support is missing')

    component_root = frontend / 'src/app/shared/ui'
    for component in COMPONENTS:
        component_dir = component_root / component
        ts_files = list(component_dir.glob('*.component.ts'))
        if len(ts_files) != 1:
            errors.append(f'{component}: expected exactly one component TypeScript file')
            continue
        source = ts_files[0].read_text(encoding='utf-8')
        if 'ChangeDetectionStrategy.OnPush' not in source:
            errors.append(f'{component}: OnPush change detection is required')
        for scss in component_dir.glob('*.scss'):
            if HEX_PATTERN.search(scss.read_text(encoding='utf-8')):
                errors.append(f'{scss.relative_to(repo)}: component styles must use semantic tokens, not hex colors')

    theme_service = frontend / 'src/app/shared/theme/ui-theme.service.ts'
    if not theme_service.is_file():
        errors.append('UiThemeService is missing')
    else:
        text = theme_service.read_text(encoding='utf-8')
        for required in ('localStorage', 'matchMedia', "dataset['theme']"):
            if required not in text:
                errors.append(f'UiThemeService: missing {required}')

    app_template = (frontend / 'src/app/app.component.html').read_text(encoding='utf-8')
    for required in ('app-ui-theme-toggle', 'app-ui-button', 'app-ui-input', 'app-ui-textarea', 'Ask AI preview'):
        if required not in app_template:
            errors.append(f'app.component.html: missing {required}')
    if '/agent/actions/' in app_template or 'http://127.0.0.1:8000' in app_template:
        errors.append('app.component.html: raw backend implementation detail is exposed')

    if not (frontend / 'docs/DESIGN_SYSTEM.md').is_file():
        errors.append('frontend/docs/DESIGN_SYSTEM.md is missing')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='.')
    args = parser.parse_args()
    errors = validate(Path(args.repo).resolve())
    if errors:
        print('Angular Phase 2 validation failed:')
        for error in errors:
            print(f'- {error}')
        return 1
    print('Angular Phase 2 design system is valid: 10 primitives, semantic themes, and showcase coverage.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
