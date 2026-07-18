import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { UiInputComponent } from './ui-input.component';

describe('UiInputComponent', () => {
  it('associates the label and validation message with the native input', async () => {
    await TestBed.configureTestingModule({ imports: [UiInputComponent] }).compileComponents();
    const fixture = TestBed.createComponent(UiInputComponent);
    fixture.componentInstance.label = 'Rule name';
    fixture.componentInstance.error = 'Already exists';
    fixture.detectChanges();
    const input = (fixture.nativeElement as HTMLElement).querySelector('input') as HTMLInputElement;
    const label = (fixture.nativeElement as HTMLElement).querySelector('label') as HTMLLabelElement;
    expect(label.htmlFor).toBe(input.id);
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe(`${input.id}-error`);
  });
});
