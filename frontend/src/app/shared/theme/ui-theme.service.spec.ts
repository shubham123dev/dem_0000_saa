import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { UiThemeService } from './ui-theme.service';

describe('UiThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    TestBed.configureTestingModule({ providers: [{ provide: DOCUMENT, useValue: document }] });
  });

  it('persists explicit theme choices and updates the document', () => {
    const service = TestBed.inject(UiThemeService);
    service.setPreference('dark');
    TestBed.tick();
    expect(service.preference()).toBe('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(localStorage.getItem('dbmr-workplace-theme')).toBe('dark');
  });
});
