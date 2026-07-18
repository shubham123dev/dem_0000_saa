import type { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { CurrentUserStore } from './current-user.store';

export const authHeaderInterceptor: HttpInterceptorFn = (request, next) => {
  const config = inject(APP_RUNTIME_CONFIG);
  const userId = inject(CurrentUserStore).userId();
  if (!userId || !request.url.startsWith(config.apiBaseUrl)) {
    return next(request);
  }
  return next(request.clone({ setHeaders: { 'X-Mock-User-Id': userId } }));
};
