import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { AppComponent } from './app.component';
import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';

describe('AppComponent', () => {
  it('renders the complete workplace shell', async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        { provide: APP_RUNTIME_CONFIG, useValue: { apiBaseUrl: '/api', defaultOrganizationId: 'org_1', mockUserId: 'usr_1', requestTimeoutMs: 30000, enableDebugViews: false, streamTransport: 'rest' as const } }
      ]
    }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain("Let's get to work.");
    expect(element.querySelector('[aria-label="Primary navigation"]')).not.toBeNull();
    expect(element.querySelector('[aria-label="Ask AI"]')).not.toBeNull();
  });
});
