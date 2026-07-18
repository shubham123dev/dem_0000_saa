import { InjectionToken } from '@angular/core';
import type { AppRuntimeConfig } from './app-config.model';

export const APP_RUNTIME_CONFIG = new InjectionToken<AppRuntimeConfig>('APP_RUNTIME_CONFIG');
