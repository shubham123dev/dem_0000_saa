import { describe, expect, it, vi } from 'vitest';
import { loadAppRuntimeConfig } from './app-config.loader';

describe('loadAppRuntimeConfig', () => {
  it('loads and normalizes an SSE configuration', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiBaseUrl:'/api/', defaultOrganizationId:'org_1', mockUserId:'usr_1', requestTimeoutMs:30000, enableDebugViews:false, streamTransport:'sse' }), {status:200, headers:{'content-type':'application/json'}}));
    const result = await loadAppRuntimeConfig('/config/app-config.json', fetcher);
    expect(result.apiBaseUrl).toBe('/api');
    expect(result.streamTransport).toBe('sse');
  });

  it('keeps the explicit REST compatibility mode', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiBaseUrl:'/api', defaultOrganizationId:'org_1', mockUserId:'usr_1', requestTimeoutMs:30000, enableDebugViews:false, streamTransport:'rest' }), {status:200}));
    expect((await loadAppRuntimeConfig('/config/app-config.json', fetcher)).streamTransport).toBe('rest');
  });

  it('rejects unknown fields', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiBaseUrl:'/api', defaultOrganizationId:null, mockUserId:null, requestTimeoutMs:30000, enableDebugViews:false, streamTransport:'sse', unexpected:true }), {status:200}));
    await expect(loadAppRuntimeConfig('/config/app-config.json', fetcher)).rejects.toThrow();
  });
});
