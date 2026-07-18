import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import type { UiThemePreference } from './ui-theme.model';
import { UiThemeService } from './ui-theme.service';

interface ThemeOption {
  value: UiThemePreference;
  label: string;
  glyph: string;
}

@Component({
  selector: 'app-ui-theme-toggle',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-theme-toggle.component.html',
  styleUrl: './ui-theme-toggle.component.scss'
})
export class UiThemeToggleComponent {
  readonly theme = inject(UiThemeService);
  readonly options: readonly ThemeOption[] = [
    { value: 'system', label: 'Use system theme', glyph: '◐' },
    { value: 'light', label: 'Use light theme', glyph: '☀' },
    { value: 'dark', label: 'Use dark theme', glyph: '☾' }
  ];

  select(preference: UiThemePreference): void {
    this.theme.setPreference(preference);
  }
}
