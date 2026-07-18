export type UiThemePreference = 'system' | 'light' | 'dark';
export type UiResolvedTheme = Exclude<UiThemePreference, 'system'>;
