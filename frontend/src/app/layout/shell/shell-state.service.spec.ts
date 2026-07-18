import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { ShellStateService } from './shell-state.service';

describe('ShellStateService', () => {
  beforeEach(() => { localStorage.clear(); TestBed.configureTestingModule({}); });
  it('clamps and persists the assistant width', () => {
    const service = TestBed.inject(ShellStateService);
    service.setAssistantWidth(900);
    TestBed.tick();
    expect(service.assistantWidth()).toBe(608);
    expect(localStorage.getItem('dbmr-workplace-assistant-width')).toBe('608');
  });
  it('updates the active workspace section', () => {
    const service = TestBed.inject(ShellStateService);
    service.selectSection('users');
    expect(service.activeSection()).toBe('users');
  });
});
