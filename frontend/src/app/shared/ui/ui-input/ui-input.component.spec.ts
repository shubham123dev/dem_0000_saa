import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { describe, expect, it } from 'vitest';
import { UiInputComponent } from './ui-input.component';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, UiInputComponent],
  template: '<app-ui-input label="Rule name" [formControl]="control" />'
})
class InputHostComponent { readonly control = new FormControl('Initial', { nonNullable: true }); }

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

  it('integrates with reactive forms in both directions', async () => {
    await TestBed.configureTestingModule({ imports: [InputHostComponent] }).compileComponents();
    const fixture = TestBed.createComponent(InputHostComponent);
    fixture.detectChanges();
    const input = (fixture.nativeElement as HTMLElement).querySelector('input') as HTMLInputElement;
    expect(input.value).toBe('Initial');
    fixture.componentInstance.control.setValue('Updated');
    fixture.detectChanges();
    expect(input.value).toBe('Updated');
    input.value = 'Typed';
    input.dispatchEvent(new Event('input'));
    expect(fixture.componentInstance.control.value).toBe('Typed');
  });
});
