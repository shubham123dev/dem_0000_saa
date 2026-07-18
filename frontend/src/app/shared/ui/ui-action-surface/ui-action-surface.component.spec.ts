import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { UiActionSurfaceComponent } from './ui-action-surface.component';

describe('UiActionSurfaceComponent', () => {
  it('uses native button keyboard semantics and emits activation', async () => {
    await TestBed.configureTestingModule({ imports: [UiActionSurfaceComponent] }).compileComponents();
    const fixture = TestBed.createComponent(UiActionSurfaceComponent);
    fixture.componentInstance.heading = 'Users';
    const activated = vi.fn();
    fixture.componentInstance.activated.subscribe(activated);
    fixture.detectChanges();
    const button = (fixture.nativeElement as HTMLElement).querySelector('button') as HTMLButtonElement;
    button.click();
    expect(activated).toHaveBeenCalledOnce();
    expect(button.type).toBe('button');
  });
});
