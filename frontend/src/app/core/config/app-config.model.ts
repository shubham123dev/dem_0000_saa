import { z } from 'zod';

function isSupportedApiBaseUrl(value: string): boolean {
  if (value.startsWith('/') && !value.startsWith('//')) return value.length > 1;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

const apiBaseUrlSchema = z.string().trim().min(1).refine(
  isSupportedApiBaseUrl,
  'apiBaseUrl must be a root-relative path or an HTTP(S) URL.'
).transform((value) => value.replace(/\/+$/, ''));

export const appRuntimeConfigSchema = z.object({
  apiBaseUrl: apiBaseUrlSchema,
  defaultOrganizationId: z.string().trim().min(1).nullable(),
  mockUserId: z.string().trim().min(1).nullable(),
  requestTimeoutMs: z.number().int().min(1000).max(120000),
  enableDebugViews: z.boolean(),
  streamTransport: z.enum(['sse', 'rest'])
}).strict();

export type AppRuntimeConfig = z.infer<typeof appRuntimeConfigSchema>;
