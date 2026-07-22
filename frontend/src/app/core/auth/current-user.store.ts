import { computed, inject, Injectable, signal } from '@angular/core';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';

export interface UserProfile {
  id: string;
  display_name: string;
  email: string;
  status: string;
  created_at?: string;
  entitlements: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class CurrentUserStore {
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly configuredUserId = this.config.mockUserId;
  private readonly configuredOrgId = this.config.defaultOrganizationId;
  private readonly userState = signal<UserProfile | null>(null);
  private readonly userIdState = signal<string | null>(this.configuredUserId);

  readonly user = this.userState.asReadonly();
  readonly userId = computed(() => this.user()?.id ?? this.userIdState());
  readonly isAuthenticated = computed(() => this.userId() !== null);
  readonly entitlements = computed(() => this.user()?.entitlements ?? {});

  readonly organizationId = computed<string | null>(() => {
    const userProfile = this.user();
    if (userProfile) {
      const orgId = userProfile.entitlements['OrganizationId'];
      if (orgId !== null && orgId !== undefined && String(orgId).trim()) {
        const cleaned = String(orgId).trim();
        if (cleaned.startsWith('org_')) return cleaned;
        return `org_sandbox_${cleaned.padStart(3, '0')}`;
      }
    }
    return this.configuredOrgId ?? null;
  });

  setUserProfile(profile: UserProfile | null): void {
    this.userState.set(profile);
    if (profile) {
      this.userIdState.set(profile.id);
    }
  }

  setSandboxUser(userId: string | null): void {
    const normalized = userId?.trim() ?? null;
    this.userIdState.set(normalized || null);
    if (!normalized) {
      this.userState.set(null);
    }
  }

  clearUser(): void {
    this.userState.set(null);
    this.userIdState.set(null);
  }
}
