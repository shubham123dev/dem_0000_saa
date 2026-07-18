import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { AssistantComposerComponent } from './assistant-composer.component';

describe('AssistantComposerComponent', () => {
  it('submits on Enter, preserves Shift+Enter, and clears the draft', async () => {
    await TestBed.configureTestingModule({ imports:[AssistantComposerComponent] }).compileComponents();
    const fixture=TestBed.createComponent(AssistantComposerComponent);
    const submitted=vi.fn();
    fixture.componentInstance.submitted.subscribe(submitted);
    fixture.componentInstance.draft.set('Show active users');
    fixture.detectChanges();
    fixture.componentInstance.keydown(new KeyboardEvent('keydown',{key:'Enter'}));
    expect(submitted).toHaveBeenCalledWith('Show active users');
    expect(fixture.componentInstance.draft()).toBe('');
  });
});
