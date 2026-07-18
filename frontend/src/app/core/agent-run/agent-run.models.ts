import type { z } from 'zod';
import type {
  agentConversationResponseSchema,
  agentRunCreateRequestSchema,
  agentRunCreateResponseSchema,
  agentRunEventSchema,
  agentRunMessageSchema,
  agentRunSchema
} from './agent-run.schemas';

export type AgentRunCreateRequest = z.input<typeof agentRunCreateRequestSchema>;
export type AgentRunCreateResponse = z.infer<typeof agentRunCreateResponseSchema>;
export type AgentConversationResponse = z.infer<typeof agentConversationResponseSchema>;
export type AgentRun = z.infer<typeof agentRunSchema>;
export type AgentRunMessage = z.infer<typeof agentRunMessageSchema>;
export type AgentRunEvent = z.infer<typeof agentRunEventSchema>;
export type AgentRunConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed';
export type AgentRunStreamUpdate =
  | { readonly kind: 'state'; readonly state: AgentRunConnectionState }
  | { readonly kind: 'event'; readonly event: AgentRunEvent };
