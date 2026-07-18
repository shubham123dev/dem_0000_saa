import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { AppComponent } from './app.component';
import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';

const config = {
  apiBaseUrl: '/api',
  defaultOrganizationId: 'org_1',
  mockUserId: 'usr_1',
  requestTimeoutMs: 30000,
  enableDebugViews: false,
  streamTransport: 'rest' as const
};

describe('AppComponent', () => {
  it('renders the Phase 2 design-system showcase without backend endpoints', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent], providers: [{ provide: APP_RUNTIME_CONFIG, useValue: config }] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain('Cloudflare-quality Angular primitives');
    expect(element.textContent).toContain('Approve');
    expect(element.textContent).not.toContain('/agent/actions/propose');
  });
});
