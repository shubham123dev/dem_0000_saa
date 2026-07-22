/**
 * OrganizationRouteService — single source of truth for the active
 * organization ID derived from the current Angular Router URL.
 *
 * Every component, store and API service that needs the "current org"
 * should inject this service instead of reading from config or user
 * entitlements directly.
 *
 * When no `:orgId` route parameter is present (e.g. on the landing
 * page), the service falls back to the user's default organization
 * from their entitlements.
 */
import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { CurrentUserStore } from '../auth/current-user.store';

@Injectable({ providedIn: 'root' })
export class OrganizationRouteService {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly currentUser = inject(CurrentUserStore);

  /** Raw `:orgId` extracted from the deepest activated route snapshot. */
  private readonly routeOrgIdState = signal<string | null>(null);

  /** The organization ID from the URL, or the user's default as fallback. */
  readonly organizationId = computed<string | null>(() =>
    this.routeOrgIdState() ?? this.currentUser.organizationId()
  );

  /** True when the org ID is explicitly present in the URL. */
  readonly isRouteScoped = computed(() => this.routeOrgIdState() !== null);

  constructor() {
    // Sync from initial navigation and every subsequent navigation
    this.syncFromSnapshot();
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(() => this.syncFromSnapshot());
  }

  /** Walk the activated route tree to find the deepest `:orgId` param. */
  private syncFromSnapshot(): void {
    let route: ActivatedRoute | null = this.router.routerState.root;
    let orgId: string | null = null;

    while (route) {
      const paramValue = route.snapshot.paramMap.get('orgId');
      if (paramValue) {
        orgId = paramValue;
      }
      route = route.firstChild;
    }

    this.routeOrgIdState.set(orgId);
  }
}
