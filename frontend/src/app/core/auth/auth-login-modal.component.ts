import { ChangeDetectionStrategy, Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';
import { UiButtonComponent, UiCalloutComponent } from '../../shared/ui';

@Component({
  selector: 'app-auth-login-modal',
  standalone: true,
  imports: [FormsModule, UiButtonComponent, UiCalloutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="auth-modal-backdrop" (click)="closeModal()">
      <div class="auth-modal" (click)="$event.stopPropagation()">
        <header class="auth-modal__header">
          <div class="auth-modal__title">
            <img src="sara-ai-orb.svg" alt="" aria-hidden="true" class="auth-modal__orb" />
            <h3>Sign in to DBMR Workplace Agent</h3>
          </div>
          <button type="button" class="auth-modal__close" (click)="closeModal()" aria-label="Close">×</button>
        </header>

        <div class="auth-modal__body">
          <p class="auth-modal__subtitle">
            Enter your registered email address to authenticate with <code>dbo.Test_user1</code> and unlock Ask SARA.
          </p>

          @if (errorMessage()) {
            <app-ui-callout tone="danger" title="Authentication Error">
              {{ errorMessage() }}
            </app-ui-callout>
          }

          <form (ngSubmit)="submitLogin()" class="auth-modal__form">
            <label class="auth-modal__label" for="login-email">
              Registered Email Address
            </label>
            <input
              id="login-email"
              type="email"
              class="auth-modal__input"
              placeholder="Enter your registered email address"
              [(ngModel)]="email"
              name="email"
              [disabled]="loading()"
              required
            />

            <label class="auth-modal__label" for="login-password">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              class="auth-modal__input"
              placeholder="Enter your account password"
              [(ngModel)]="password"
              name="password"
              [disabled]="loading()"
            />

            <div class="auth-modal__actions">
              <app-ui-button
                buttonType="button"
                variant="outline"
                [disabled]="loading()"
                (pressed)="closeModal()"
              >
                Cancel
              </app-ui-button>
              <app-ui-button
                buttonType="submit"
                variant="primary"
                [disabled]="loading() || !email().trim()"
                (pressed)="submitLogin()"
              >
                {{ loading() ? 'Authenticating...' : 'Sign In' }}
              </app-ui-button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 1000;
      background: rgba(8, 10, 16, 0.72);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }

    .auth-modal {
      width: 100%;
      max-width: 440px;
      background: linear-gradient(165deg, #1c2033 0%, #111422 100%);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-top: 1px solid rgba(255, 255, 255, 0.22);
      border-radius: 18px;
      box-shadow: 0 28px 64px -12px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.08);
      overflow: hidden;
      color: #f8fafc;
      animation: modalFadeIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.95) translateY(10px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }

    .auth-modal__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 100%);
    }

    .auth-modal__title {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      h3 {
        margin: 0;
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: #ffffff;
      }
    }

    .auth-modal__orb {
      width: 26px;
      height: 26px;
      filter: drop-shadow(0 0 8px rgba(168, 85, 247, 0.5));
    }

    .auth-modal__close {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
      padding: 0.25rem;
      transition: color 0.15s ease;
      &:hover { color: #ffffff; }
    }

    .auth-modal__body {
      padding: 1.5rem;
    }

    .auth-modal__subtitle {
      margin: 0 0 1.25rem 0;
      font-size: 0.92rem;
      color: #cbd5e1;
      line-height: 1.45;

      code {
        background: rgba(255, 255, 255, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.25);
        padding: 0.15rem 0.4rem;
        border-radius: 5px;
        font-size: 0.85rem;
        font-weight: 600;
      }
    }

    .auth-modal__form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .auth-modal__label {
      font-size: 0.85rem;
      font-weight: 600;
      color: #f1f5f9;
      letter-spacing: 0.01em;
    }

    .auth-modal__input {
      width: 100%;
      padding: 0.75rem 0.95rem;
      background: rgba(15, 18, 28, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      color: #ffffff;
      font-size: 0.95rem;
      outline: none;
      transition: all 0.15s ease;

      &::placeholder {
        color: #64748b;
      }

      &:focus {
        background: rgba(15, 18, 28, 0.95);
        border-color: #f97316;
        box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.25);
      }
    }

    .auth-modal__actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      margin-top: 0.75rem;

      ::ng-deep button[data-variant="outline"],
      ::ng-deep .ui-button--outline {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        color: #cbd5e1 !important;
        box-shadow: none !important;

        &:hover {
          background: rgba(255, 255, 255, 0.12) !important;
          color: #ffffff !important;
          border-color: rgba(255, 255, 255, 0.25) !important;
        }
      }
    }
  `]
})
export class AuthLoginModalComponent {
  private readonly auth = inject(AuthService);

  @Output() readonly loggedIn = new EventEmitter<void>();
  @Output() readonly closed = new EventEmitter<void>();

  readonly email = signal('');
  readonly password = signal('');
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  submitLogin(): void {
    const rawEmail = this.email().trim();
    if (!rawEmail) return;

    this.loading.set(true);
    this.errorMessage.set(null);

    const rawPassword = this.password().trim();
    this.auth.login({ email: rawEmail, password: rawPassword || undefined }).subscribe({
      next: () => {
        this.loading.set(false);
        this.loggedIn.emit();
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err?.error?.error?.message ?? 'Failed to authenticate user against dbo.Test_user1';
        this.errorMessage.set(msg);
      }
    });
  }

  closeModal(): void {
    if (!this.loading()) {
      this.closed.emit();
    }
  }
}
