import { appRuntimeConfigSchema, type AppRuntimeConfig } from './app-config.model';

export async function loadAppRuntimeConfig(url: string, fetcher: typeof fetch = fetch): Promise<AppRuntimeConfig> {
  const response = await fetcher(url, { cache: 'no-store', credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error(`Runtime configuration request failed with status ${response.status}.`);
  }
  const payload: unknown = await response.json();
  return appRuntimeConfigSchema.parse(payload);
}
