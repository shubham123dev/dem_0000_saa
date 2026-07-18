import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { type ApplicationConfig, provideZonelessChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { apiErrorInterceptor } from './core/api/api-error.interceptor';
import { requestIdInterceptor } from './core/api/request-id.interceptor';
import { authHeaderInterceptor } from './core/auth/auth-header.interceptor';
import type { AppRuntimeConfig } from './core/config/app-config.model';
import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';

export function createAppConfig(runtimeConfig: AppRuntimeConfig): ApplicationConfig {
  return {
    providers: [
      provideZonelessChangeDetection(),
      provideRouter(routes),
      { provide: APP_RUNTIME_CONFIG, useValue: runtimeConfig },
      provideHttpClient(withInterceptors([requestIdInterceptor, authHeaderInterceptor, apiErrorInterceptor]))
    ]
  };
}
