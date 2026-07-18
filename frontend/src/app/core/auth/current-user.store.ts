import { computed, inject, Injectable, signal } from '@angular/core';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';

@Injectable({ providedIn: 'root' })
export class CurrentUserStore {
  private readonly configuredUserId = inject(APP_RUNTIME_CONFIG).mockUserId;
  private readonly userIdState = signal<string | null>(this.configuredUserId);
  readonly userId = this.userIdState.asReadonly();
  readonly isAuthenticated = computed(() => this.userId() !== null);

  setSandboxUser(userId: string | null): void {
    const normalized = userId?.trim() ?? null;
    this.userIdState.set(normalized || null);
  }
}
