import { DOCUMENT } from '@angular/common';
import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import type { UiResolvedTheme, UiThemePreference } from './ui-theme.model';

const STORAGE_KEY = 'dbmr-workplace-theme';
const DARK_QUERY = '(prefers-color-scheme: dark)';

function isThemePreference(value: string | null): value is UiThemePreference {
  return value === 'system' || value === 'light' || value === 'dark';
}

@Injectable({ providedIn: 'root' })
export class UiThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly mediaQuery = this.document.defaultView?.matchMedia?.(DARK_QUERY) ?? null;
  private readonly systemDarkState = signal(this.mediaQuery?.matches ?? false);
  private readonly preferenceState = signal<UiThemePreference>(this.readPreference());

  readonly preference = this.preferenceState.asReadonly();
  readonly resolvedTheme = computed<UiResolvedTheme>(() => {
    const preference = this.preference();
    return preference === 'system' ? (this.systemDarkState() ? 'dark' : 'light') : preference;
  });

  constructor() {
    const onSystemThemeChange = (event: MediaQueryListEvent): void => this.systemDarkState.set(event.matches);
    this.mediaQuery?.addEventListener('change', onSystemThemeChange);
    this.destroyRef.onDestroy(() => this.mediaQuery?.removeEventListener('change', onSystemThemeChange));

    effect(() => {
      const preference = this.preference();
      const resolvedTheme = this.resolvedTheme();
      const root = this.document.documentElement;
      root.dataset['theme'] = resolvedTheme;
      root.dataset['themePreference'] = preference;
      root.style.colorScheme = resolvedTheme;
    });
  }

  setPreference(preference: UiThemePreference): void {
    this.preferenceState.set(preference);
    this.writePreference(preference);
  }

  private readPreference(): UiThemePreference {
    try {
      const stored = this.document.defaultView?.localStorage.getItem(STORAGE_KEY) ?? null;
      return isThemePreference(stored) ? stored : 'system';
    } catch {
      return 'system';
    }
  }

  private writePreference(preference: UiThemePreference): void {
    try {
      this.document.defaultView?.localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // Storage may be disabled; the in-memory preference still applies.
    }
  }
}
