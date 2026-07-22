/**
 * Authentication route guard.
 *
 * Protects organization-scoped routes by ensuring the user is
 * authenticated before rendering.
 *
 * Flow:
 * 1. If CurrentUserStore already has an authenticated user → allow.
 * 2. Otherwise, attempt a cookie-based session restore via GET /auth/me.
 * 3. If session restore succeeds → allow.
 * 4. If session restore fails → redirect to root `/` (landing page).
 */
import { inject } from '@angular/core';
import { type CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { CurrentUserStore } from '../auth/current-user.store';

export const authGuard: CanActivateFn = () => {
  const userStore = inject(CurrentUserStore);
  const authService = inject(AuthService);
  const router = inject(Router);

  // Already authenticated — allow immediately
  if (userStore.isAuthenticated()) {
    return true;
  }

  // Attempt cookie-based session restore
  return authService.getMe().pipe(
    map((profile) => {
      if (profile) {
        return true;
      }
      return router.createUrlTree(['/']);
    }),
    catchError(() => of(router.createUrlTree(['/'])))
  );
};
