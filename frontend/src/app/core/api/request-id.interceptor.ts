import type { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';

function createRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const requestIdInterceptor: HttpInterceptorFn = (request, next) => {
  const config = inject(APP_RUNTIME_CONFIG);
  if (!request.url.startsWith(config.apiBaseUrl) || request.headers.has('X-Request-Id')) {
    return next(request);
  }
  return next(request.clone({ setHeaders: { 'X-Request-Id': createRequestId() } }));
};
