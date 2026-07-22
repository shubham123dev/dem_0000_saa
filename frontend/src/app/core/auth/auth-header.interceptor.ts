import type { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { CurrentUserStore } from './current-user.store';

export const authHeaderInterceptor: HttpInterceptorFn = (request, next) => {
  const config = inject(APP_RUNTIME_CONFIG);
  const userId = inject(CurrentUserStore).userId();

  // Ensure all API calls targeting the backend include HTTP-only cookies
  const isApiRequest = request.url.startsWith(config.apiBaseUrl);
  if (!isApiRequest) {
    return next(request);
  }

  const clonedHeaders: Record<string, string> = {};
  if (userId) {
    clonedHeaders['X-Mock-User-Id'] = userId;
  }

  return next(
    request.clone({
      withCredentials: true,
      setHeaders: clonedHeaders,
    })
  );
};
