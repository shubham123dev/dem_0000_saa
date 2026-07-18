import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { describe, expect, it } from 'vitest';
import { UiTextareaComponent } from './ui-textarea.component';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, UiTextareaComponent],
  template: '<app-ui-textarea label="Message" [formControl]="control" />'
})
class TextareaHostComponent { readonly control = new FormControl('Initial note', { nonNullable: true }); }

describe('UiTextareaComponent', () => {
  it('integrates with reactive forms and marks the native control disabled', async () => {
    await TestBed.configureTestingModule({ imports: [TextareaHostComponent] }).compileComponents();
    const fixture = TestBed.createComponent(TextareaHostComponent);
    fixture.detectChanges();
    const textarea = (fixture.nativeElement as HTMLElement).querySelector('textarea') as HTMLTextAreaElement;
    expect(textarea.value).toBe('Initial note');
    textarea.value = 'Updated note';
    textarea.dispatchEvent(new Event('input'));
    expect(fixture.componentInstance.control.value).toBe('Updated note');
    fixture.componentInstance.control.disable();
    fixture.detectChanges();
    expect(textarea.disabled).toBe(true);
  });
});
