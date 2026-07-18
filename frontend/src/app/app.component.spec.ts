import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
  it('renders the complete workplace shell', async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain("Let's get to work.");
    expect(element.querySelector('[aria-label="Primary navigation"]')).not.toBeNull();
    expect(element.querySelector('[aria-label="Ask AI"]')).not.toBeNull();
  });
});
