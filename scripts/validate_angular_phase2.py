#!/usr/bin/env python3
from __future__ import annotations
import argparse, math, re
from pathlib import Path

COMPONENTS = ('ui-action-surface','ui-badge','ui-button','ui-callout','ui-icon-button','ui-input','ui-skeleton','ui-spinner','ui-status-indicator','ui-surface','ui-textarea')
HEX = re.compile(r'#[0-9a-fA-F]{6}\b')

def _rgb(value: str) -> tuple[float,float,float]:
    value=value.lstrip('#'); return tuple(int(value[i:i+2],16)/255 for i in (0,2,4))  # type: ignore[return-value]
def _luminance(value: str) -> float:
    channels=[c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4 for c in _rgb(value)]
    return 0.2126*channels[0]+0.7152*channels[1]+0.0722*channels[2]
def contrast(a: str,b: str) -> float:
    high,low=sorted((_luminance(a),_luminance(b)),reverse=True); return (high+0.05)/(low+0.05)
def _token(text: str,name: str) -> str | None:
    match=re.search(rf'{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})',text); return match.group(1) if match else None

def validate(repo: Path) -> list[str]:
    errors=[]; frontend=repo/'frontend'; styles=frontend/'src/styles'; tokens=(styles/'_tokens.scss').read_text(encoding='utf-8')
    for component in COMPONENTS:
        directory=frontend/'src/app/shared/ui'/component
        sources=list(directory.glob('*.component.ts'))
        if len(sources)!=1: errors.append(f'{component}: expected exactly one component TypeScript file'); continue
        if 'ChangeDetectionStrategy.OnPush' not in sources[0].read_text(encoding='utf-8'): errors.append(f'{component}: OnPush is required')
        for scss in directory.glob('*.scss'):
            if HEX.search(scss.read_text(encoding='utf-8')): errors.append(f'{scss.relative_to(repo)}: component styles must use tokens')
    index=(frontend/'src/index.html').read_text(encoding='utf-8')
    for required in ('dbmr-workplace-theme',"dataset['theme']",'prefers-color-scheme: dark'):
        if required not in index: errors.append(f'index.html: missing pre-bootstrap theme behavior {required}')
    for rel in ('src/app/shared/ui/ui-input/ui-input.component.ts','src/app/shared/ui/ui-textarea/ui-textarea.component.ts'):
        text=(frontend/rel).read_text(encoding='utf-8')
        for required in ('ControlValueAccessor','NG_VALUE_ACCESSOR','writeValue','setDisabledState'):
            if required not in text: errors.append(f'{rel}: missing {required}')
    surface=(frontend/'src/app/shared/ui/ui-surface/ui-surface.component.ts').read_text(encoding='utf-8')
    if 'interactive' in surface: errors.append('UiSurface must remain presentational')
    action=(frontend/'src/app/shared/ui/ui-action-surface/ui-action-surface.component.html').read_text(encoding='utf-8')
    if '<button' not in action: errors.append('UiActionSurface must use a native button')
    visible='\n'.join(path.read_text(encoding='utf-8') for path in (frontend/'src/app').rglob('*.html'))
    for forbidden in ('Cloudflare','currentUser.userId()','organizationId','/agent/actions/'):
        if forbidden in visible: errors.append(f'visible templates expose forbidden value: {forbidden}')
    brand=_token(tokens,'--ui-brand-600'); dark=_token(tokens,'--ui-neutral-950'); green=_token(tokens,'--ui-green-700'); green_bg=_token(tokens,'--ui-green-50')
    if not all((brand,dark,green,green_bg)): errors.append('contrast tokens are missing')
    else:
        if contrast(brand,dark)<4.5: errors.append('brand hover contrast is below 4.5:1')
        if contrast(green,green_bg)<4.5: errors.append('success contrast is below 4.5:1')
    return errors

def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())
    if errors:
        print('Angular Phase 2 hardening validation failed:');[print(f'- {e}') for e in errors];return 1
    print('Angular Phase 2 hardening is valid: contrast, theme bootstrap, forms, semantics, and exposure checks pass.');return 0
if __name__=='__main__': raise SystemExit(main())
