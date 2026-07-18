import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { UiButtonComponent } from './ui-button.component';

describe('UiButtonComponent', () => {
  it('blocks activation and exposes busy state while loading', async () => {
    await TestBed.configureTestingModule({ imports: [UiButtonComponent] }).compileComponents();
    const fixture = TestBed.createComponent(UiButtonComponent);
    const emitted = vi.fn();
    fixture.componentInstance.loading = true;
    fixture.componentInstance.pressed.subscribe(emitted);
    fixture.detectChanges();
    const button = (fixture.nativeElement as HTMLElement).querySelector('button') as HTMLButtonElement;
    button.click();
    expect(button.disabled).toBe(true);
    expect(button.getAttribute('aria-busy')).toBe('true');
    expect(emitted).not.toHaveBeenCalled();
  });
});
