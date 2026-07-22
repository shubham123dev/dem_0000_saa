/**
 * LandingComponent — root redirect page at `/`.
 *
 * If the user is already authenticated and has a default organization,
 * it redirects to `/organizations/{orgId}` automatically.
 * Otherwise it displays a sign-in prompt.
 */
import { ChangeDetectionStrategy, Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { CurrentUserStore } from '../../core/auth/current-user.store';
import { AuthLoginModalComponent } from '../../core/auth/auth-login-modal.component';
import { UiButtonComponent, UiCalloutComponent } from '../../shared/ui';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [AuthLoginModalComponent, UiButtonComponent, UiCalloutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="landing">
      <div class="landing__card">
        <img class="landing__orb" src="sara-ai-orb.svg" alt="" aria-hidden="true" />
        <h1>DBMR Workplace Agent</h1>
        <p class="landing__subtitle">
          Sign in with your registered email to access your organization workspace.
        </p>

        @if (userStore.isAuthenticated() && !userStore.organizationId()) {
          <app-ui-callout tone="danger" title="No Organization Assigned">
            Your account does not have an OrganizationID assigned in
            <code>dbo.Test_user1</code>. Contact your workspace administrator.
          </app-ui-callout>
        } @else if (!userStore.isAuthenticated()) {
          <app-ui-button variant="primary" (pressed)="showLogin = true">
            Sign in to continue
          </app-ui-button>
        }
      </div>

      @if (showLogin) {
        <app-auth-login-modal
          (loggedIn)="onLoggedIn()"
          (closed)="showLogin = false"
        />
      }
    </div>
  `,
  styles: [`
    .landing {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      min-height: 100dvh;
      padding: 2rem;
      background: var(--ui-surface-base, #0a0c14);
    }

    .landing__card {
      text-align: center;
      max-width: 420px;
      padding: 3rem 2.5rem;
      background: linear-gradient(165deg, #1c2033 0%, #111422 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      box-shadow: 0 32px 72px -16px rgba(0, 0, 0, 0.6);
      color: #f8fafc;
      animation: fadeUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .landing__orb {
      width: 56px;
      height: 56px;
      margin-bottom: 1.25rem;
      filter: drop-shadow(0 0 16px rgba(168, 85, 247, 0.5));
    }

    h1 {
      margin: 0 0 0.5rem;
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .landing__subtitle {
      color: #94a3b8;
      font-size: 0.95rem;
      line-height: 1.5;
      margin: 0 0 1.5rem;
    }

    code {
      background: rgba(255, 255, 255, 0.1);
      color: #38bdf8;
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }
  `]
})
export class LandingComponent implements OnInit {
  readonly userStore = inject(CurrentUserStore);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  showLogin = false;

  ngOnInit(): void {
    // Attempt session restore; if successful and has org, redirect
    this.auth.getMe().subscribe((profile) => {
      if (profile) {
        this.tryRedirect();
      }
    });
  }

  onLoggedIn(): void {
    this.showLogin = false;
    this.tryRedirect();
  }

  private tryRedirect(): void {
    const orgId = this.userStore.organizationId();
    if (orgId) {
      this.router.navigate(['/organizations', orgId]);
    }
  }
}
