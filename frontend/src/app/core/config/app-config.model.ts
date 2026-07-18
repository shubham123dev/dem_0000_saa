import { z } from 'zod';

export const appRuntimeConfigSchema = z.object({
  apiBaseUrl: z.url().transform((value) => value.replace(/\/$/, '')),
  defaultOrganizationId: z.string().trim().min(1).nullable(),
  mockUserId: z.string().trim().min(1).nullable(),
  requestTimeoutMs: z.number().int().min(1000).max(120000),
  enableDebugViews: z.boolean(),
  streamTransport: z.literal('rest')
}).strict();

export type AppRuntimeConfig = z.infer<typeof appRuntimeConfigSchema>;
